"""
Calendar Manager — Google Calendar integration for scheduling, rescheduling,
and AI-powered weekly summaries. Falls back gracefully without credentials.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger("CalendarManager")


def _dt_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


class CalendarManager:
    """
    Google Calendar manager + AI weekly summarizer.
    Works in mock mode without credentials — set GOOGLE env vars for live integration.
    """

    MOCK_EVENTS = [
        {"id": "ev001", "title": "Team Standup", "start": "09:00", "end": "09:30", "date": "today", "recurring": True},
        {"id": "ev002", "title": "Client Review Call", "start": "14:00", "end": "15:00", "date": "today", "recurring": False},
        {"id": "ev003", "title": "ML Project Sync", "start": "11:00", "end": "11:45", "date": "tomorrow", "recurring": True},
        {"id": "ev004", "title": "Architecture Planning", "start": "15:30", "end": "16:30", "date": "tomorrow", "recurring": False},
        {"id": "ev005", "title": "Weekly Retrospective", "start": "16:00", "end": "17:00", "date": "+2", "recurring": True},
        {"id": "ev006", "title": "Product Demo", "start": "10:00", "end": "11:30", "date": "+3", "recurring": False},
    ]

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.events: List[Dict] = []
        self._google_available = False
        self._service = None
        self._state_path = "calendar_events.json"
        self._init_google()
        self._load_state()

    def _init_google(self):
        """Try to initialize Google Calendar API."""
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        token_file = "google_token.json"

        if not (client_id and client_secret):
            logger.info("Google Calendar: No credentials. Running in mock mode.")
            logger.info("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable real Google Calendar.")
            return

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/calendar"]
            creds = None

            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)

            if not creds or not creds.valid:
                logger.info("Google Calendar credentials need refresh — use /calendar auth to re-authorize")
                return

            self._service = build("calendar", "v3", credentials=creds)
            self._google_available = True
            logger.info("✅ Google Calendar connected")
        except ImportError:
            logger.info("google-api-python-client not installed. Run: pip install google-api-python-client google-auth-oauthlib")
        except Exception as e:
            logger.warning(f"Google Calendar init error: {e}")

    def _load_state(self):
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path) as f:
                    self.events = json.load(f)
        except Exception:
            self.events = []

    def _save_state(self):
        try:
            with open(self._state_path, "w") as f:
                json.dump(self.events, f, indent=2, default=str)
        except Exception:
            pass

    def _resolve_date(self, date_str: str) -> datetime:
        today = datetime.now().replace(second=0, microsecond=0)
        if date_str == "today":
            return today
        elif date_str == "tomorrow":
            return today + timedelta(days=1)
        elif date_str.startswith("+"):
            return today + timedelta(days=int(date_str[1:]))
        else:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return today

    def list_events(self, days: int = 7) -> List[Dict]:
        """List upcoming events for the next N days."""
        if self._google_available and self._service:
            return self._google_list_events(days)
        return self._mock_list_events(days)

    def _google_list_events(self, days: int) -> List[Dict]:
        """Fetch events from Google Calendar."""
        try:
            now = datetime.utcnow()
            end = now + timedelta(days=days)
            result = self._service.events().list(
                calendarId="primary",
                timeMin=now.isoformat() + "Z",
                timeMax=end.isoformat() + "Z",
                maxResults=50,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            items = result.get("items", [])
            events = []
            for item in items:
                start = item.get("start", {})
                end_t = item.get("end", {})
                events.append({
                    "id": item.get("id"),
                    "title": item.get("summary", "Untitled"),
                    "start": start.get("dateTime", start.get("date", "")),
                    "end": end_t.get("dateTime", end_t.get("date", "")),
                    "description": item.get("description", ""),
                    "source": "google"
                })
            return events
        except Exception as e:
            logger.error(f"Google Calendar list error: {e}")
            return self._mock_list_events(days)

    def _mock_list_events(self, days: int) -> List[Dict]:
        """Return mock events for demonstration."""
        events = []
        today = datetime.now()
        for me in self.MOCK_EVENTS:
            event_date = self._resolve_date(me["date"])
            if 0 <= (event_date.date() - today.date()).days <= days:
                events.append({
                    "id": me["id"],
                    "title": me["title"],
                    "start": f"{event_date.strftime('%Y-%m-%d')} {me['start']}",
                    "end": f"{event_date.strftime('%Y-%m-%d')} {me['end']}",
                    "recurring": me.get("recurring", False),
                    "source": "mock"
                })
        # Add user-created events
        for ev in self.events:
            ev_date = datetime.fromisoformat(ev["start"]) if isinstance(ev.get("start"), str) else today
            if 0 <= (ev_date.date() - today.date()).days <= days:
                events.append(ev)
        return sorted(events, key=lambda x: x.get("start", ""))

    def create_event(self, title: str, start_str: str, duration_minutes: int = 60,
                     description: str = "") -> Dict[str, Any]:
        """Create a new calendar event."""
        try:
            # Parse start time
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
                except ValueError:
                    return {"error": f"Invalid date format: '{start_str}'. Use YYYY-MM-DD HH:MM"}

            end_dt = start_dt + timedelta(minutes=duration_minutes)

            event = {
                "id": f"local_{len(self.events)+1:04d}",
                "title": title,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "description": description,
                "created_at": datetime.now().isoformat(),
                "source": "local"
            }

            if self._google_available and self._service:
                try:
                    g_event = {
                        "summary": title,
                        "description": description,
                        "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
                        "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}
                    }
                    result = self._service.events().insert(calendarId="primary", body=g_event).execute()
                    event["id"] = result.get("id", event["id"])
                    event["source"] = "google"
                    event["link"] = result.get("htmlLink", "")
                except Exception as e:
                    logger.warning(f"Google Calendar create failed, saving locally: {e}")

            self.events.append(event)
            self._save_state()
            return {"status": "created", "event": event}

        except Exception as e:
            return {"error": str(e)}

    def reschedule_event(self, event_id: str, new_start: str) -> Dict[str, Any]:
        """Reschedule an event to a new start time."""
        for ev in self.events:
            if ev.get("id") == event_id or event_id.lower() in ev.get("title", "").lower():
                old_start = ev.get("start", "")
                try:
                    new_dt = datetime.strptime(new_start, "%Y-%m-%d %H:%M")
                except ValueError:
                    return {"error": f"Invalid format: '{new_start}'. Use: YYYY-MM-DD HH:MM"}
                ev["start"] = new_dt.isoformat()
                self._save_state()
                return {"status": "rescheduled", "title": ev["title"],
                        "from": old_start, "to": new_dt.isoformat()}
        return {"error": f"Event '{event_id}' not found"}

    def summarize_week(self) -> str:
        """Generate an AI summary of the week's calendar."""
        events = self.list_events(days=7)
        if not events:
            return "📅 Calendar is clear for the next 7 days. No events scheduled."

        event_list = "\n".join(
            f"- {ev['title']} on {ev['start']}"
            for ev in events[:20]
        )

        if self.llm:
            try:
                prompt = (
                    f"Summarize this week's calendar schedule. "
                    f"Identify busy days, key meetings, and suggest prep time.\n\n"
                    f"EVENTS:\n{event_list}\n\n"
                    f"Write a 3-4 sentence executive summary of the week."
                )
                return self.llm.call(prompt, max_tokens=200)
            except Exception:
                pass

        return f"📅 {len(events)} events this week:\n" + "\n".join(f"  • {ev['title']}" for ev in events[:10])

    def get_today(self) -> List[Dict]:
        """Get today's events."""
        today = datetime.now().date()
        return [
            ev for ev in self.list_events(days=1)
            if ev.get("start", "").startswith(str(today))
        ]

    def get_status(self) -> Dict:
        return {
            "google_connected": self._google_available,
            "mode": "Google Calendar (live)" if self._google_available else "mock/local",
            "local_events": len(self.events),
            "setup_instructions": (
                "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET env vars and "
                "install: pip install google-api-python-client google-auth-oauthlib"
            ) if not self._google_available else "Connected"
        }
