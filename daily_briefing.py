"""
Daily Briefing — Every morning: weather + news + calendar + tasks spoken aloud.
The agent briefs you like a personal assistant at the start of each day.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("DailyBriefing")


def _get_weather(city: str = "auto") -> Dict:
    """Fetch weather from wttr.in (free, no API key needed)."""
    try:
        import urllib.request
        import urllib.parse
        location = city if city != "auto" else ""
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        current = data["current_condition"][0]
        area = data["nearest_area"][0]["areaName"][0]["value"]
        country = data["nearest_area"][0]["country"][0]["value"]
        temp_c = current["temp_C"]
        temp_f = current["temp_F"]
        desc = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        feels_like = current["FeelsLikeC"]
        return {
            "success": True,
            "city": f"{area}, {country}",
            "temp_c": temp_c,
            "temp_f": temp_f,
            "description": desc,
            "humidity": humidity,
            "feels_like_c": feels_like
        }
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
        return {
            "success": False,
            "city": city,
            "temp_c": "N/A",
            "temp_f": "N/A",
            "description": "Unable to fetch weather (no internet or wttr.in unavailable)",
            "humidity": "N/A",
            "feels_like_c": "N/A"
        }


def _get_news_headlines(count: int = 5) -> List[str]:
    """Get headlines from news_briefing module if available."""
    try:
        from news_briefing import NewsBriefing
        nb = NewsBriefing(llm_provider=None)
        articles = nb.articles[-count:] if nb.articles else []
        return [f"• {a.get('title', a.get('text', str(a)))[:100]}" for a in articles]
    except Exception:
        pass

    # Fallback: Try RSS directly
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        url = "https://feeds.bbci.co.uk/news/rss.xml"
        with urllib.request.urlopen(url, timeout=5) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        headlines = []
        for item in root.iter("item"):
            title = item.find("title")
            if title is not None and title.text:
                headlines.append(f"• {title.text[:100]}")
            if len(headlines) >= count:
                break
        return headlines
    except Exception:
        return ["• No news headlines available (check internet connection)"]


class DailyBriefing:
    """
    Morning briefing system combining weather, news, calendar, tasks, and missions.
    Reads everything aloud using TTS if voice is enabled.
    """

    def __init__(self, llm_provider=None, voice_handler=None,
                 calendar=None, missions=None, db=None):
        self.llm = llm_provider
        self.voice = voice_handler
        self.calendar = calendar
        self.missions = missions
        self.db = db
        self._city = os.getenv("WEATHER_CITY", "auto")
        self._last_briefing: Optional[Dict] = None

    def _format_calendar_summary(self, tenant_id: str = "default") -> str:
        """Get today's events from calendar or missions."""
        lines = []

        if self.calendar:
            try:
                today_events = self.calendar.get_today()
                if today_events:
                    lines.append(f"📅 {len(today_events)} events today:")
                    for ev in today_events[:5]:
                        lines.append(f"   • {ev.get('title')} at {ev.get('start','')[-5:]}")
                else:
                    lines.append("📅 Calendar: Clear today (no events)")
            except Exception as e:
                logger.debug(f"Calendar error: {e}")

        return "\n".join(lines) if lines else "📅 Calendar: No events loaded"

    def _format_missions_summary(self, tenant_id: str = "default") -> str:
        """Summarize active missions/tasks."""
        if self.missions:
            try:
                active = self.missions.list_missions(tenant_id)
                if active:
                    lines = [f"🚀 {len(active)} active missions:"]
                    for m in active[:5]:
                        lines.append(f"   • [{m['progress']}%] {m['title']}")
                    return "\n".join(lines)
            except Exception:
                pass

        if self.db:
            try:
                tasks = self.db.get_pending_tasks(tenant_id)
                if tasks:
                    return f"📋 {len(tasks)} pending tasks:\n" + "\n".join(
                        f"   • {t.get('title', 'Task')} (P{t.get('priority', '?')})" for t in tasks[:5]
                    )
            except Exception:
                pass

        return "🚀 No active missions or tasks"

    def _generate_ai_summary(self, weather: Dict, headlines: List[str],
                              cal_summary: str, missions_summary: str) -> str:
        """Generate an AI-narrated briefing."""
        if not self.llm:
            return ""
        try:
            weather_text = (
                f"{weather['description']}, {weather['temp_c']}°C in {weather['city']}"
                if weather["success"] else "Weather unavailable"
            )
            news_text = "\n".join(headlines[:3])

            prompt = (
                f"You are a personal AI assistant giving a morning briefing. "
                f"Be professional, concise, and energizing.\n\n"
                f"Today: {datetime.now().strftime('%A, %B %d, %Y')}\n"
                f"Weather: {weather_text}\n"
                f"Top News:\n{news_text}\n"
                f"Schedule:\n{cal_summary}\n"
                f"Tasks:\n{missions_summary}\n\n"
                f"Give a 3-4 sentence morning briefing that synthesizes this info. "
                f"End with a motivating closing line."
            )
            return self.llm.call(prompt, max_tokens=200)
        except Exception as e:
            logger.error(f"LLM briefing error: {e}")
            return ""

    def generate_briefing(self, tenant_id: str = "default",
                           city: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a complete morning briefing.
        Returns structured dict with all sections.
        """
        city = city or self._city
        now = datetime.now()

        # Gather all sections
        weather = _get_weather(city)
        headlines = _get_news_headlines(5)
        cal_summary = self._format_calendar_summary(tenant_id)
        missions_summary = self._format_missions_summary(tenant_id)
        ai_summary = self._generate_ai_summary(weather, headlines, cal_summary, missions_summary)

        briefing = {
            "date": now.strftime("%A, %B %d, %Y"),
            "time": now.strftime("%H:%M"),
            "weather": weather,
            "news_headlines": headlines,
            "calendar": cal_summary,
            "missions": missions_summary,
            "ai_summary": ai_summary,
            "generated_at": now.isoformat()
        }
        self._last_briefing = briefing
        return briefing

    def display(self, briefing: Optional[Dict] = None) -> str:
        """Format briefing for terminal display."""
        b = briefing or self._last_briefing
        if not b:
            return "❌ No briefing generated yet. Run /briefing first."

        lines = [
            f"\n{'='*55}",
            f"  🌅 DAILY BRIEFING — {b['date']} at {b['time']}",
            f"{'='*55}",
        ]

        # Weather
        w = b.get("weather", {})
        if w.get("success"):
            lines.append(f"\n🌤️  WEATHER — {w['city']}")
            lines.append(f"   {w['description']} | {w['temp_c']}°C ({w['temp_f']}°F)")
            lines.append(f"   Feels like: {w['feels_like_c']}°C | Humidity: {w['humidity']}%")
        else:
            lines.append(f"\n🌤️  WEATHER — {w.get('description', 'unavailable')}")

        # News
        lines.append(f"\n📰 TOP NEWS:")
        for h in b.get("news_headlines", [])[:5]:
            lines.append(f"   {h}")

        # Calendar
        lines.append(f"\n{b.get('calendar', '📅 No calendar data')}")

        # Missions
        lines.append(f"\n{b.get('missions', '🚀 No missions')}")

        # AI Summary
        ai = b.get("ai_summary", "")
        if ai:
            lines.append(f"\n🤖 AI BRIEFING:")
            lines.append(f"   {ai}")

        lines.append(f"\n{'='*55}\n")
        return "\n".join(lines)

    def speak(self, briefing: Optional[Dict] = None) -> bool:
        """Speak the briefing using TTS voice handler."""
        b = briefing or self._last_briefing
        if not b:
            return False
        if not self.voice:
            logger.warning("No voice handler connected")
            return False

        try:
            w = b.get("weather", {})
            weather_speech = (
                f"Weather update: {w['description']}, {w['temp_c']} degrees celsius in {w['city']}. "
                f"Feels like {w['feels_like_c']} degrees."
                if w.get("success") else "Weather data unavailable today."
            )

            news_lines = b.get("news_headlines", [])
            news_speech = "Top news headlines: " + " | ".join(
                h.replace("•", "").strip()[:80] for h in news_lines[:3]
            )

            ai_text = b.get("ai_summary", "")
            speech = f"Good morning! Today is {b['date']}. {weather_speech} {news_speech}"
            if ai_text:
                speech += f" {ai_text}"

            self.voice.speak(speech)
            return True
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False

    def get_status(self) -> Dict:
        return {
            "last_briefing": self._last_briefing.get("date") if self._last_briefing else None,
            "weather_city": self._city,
            "voice_available": self.voice is not None,
            "calendar_connected": self.calendar is not None,
            "tip": "Set WEATHER_CITY env var to your city name for accurate weather"
        }
