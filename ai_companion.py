"""
AI Companion Mode — Persistent persona that remembers your mood and checks in on you.
Full emotional memory across sessions. The agent becomes your digital companion.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger("AICompanion")


MOODS = {
    "happy": ["great", "amazing", "wonderful", "excited", "fantastic", "love", "joy", "smile", "yes", "awesome"],
    "sad": ["sad", "depressed", "unhappy", "down", "terrible", "awful", "cry", "lonely", "miss", "hurt"],
    "stressed": ["stressed", "anxious", "worried", "overwhelmed", "deadline", "tired", "exhausted", "busy", "pressure"],
    "angry": ["angry", "frustrated", "annoyed", "mad", "furious", "hate", "rage", "irritated"],
    "neutral": []
}

COMPANION_PERSONAS = {
    "supportive": "You are a warm, empathetic AI companion. Be supportive, encouraging, and caring.",
    "motivator": "You are an energetic, motivating AI coach. Push the user to be their best.",
    "friend": "You are a casual, fun AI friend. Keep things light, use humor, be relatable.",
    "mentor": "You are a wise AI mentor. Provide thoughtful guidance and perspective.",
}


def _detect_mood(text: str) -> str:
    text_lower = text.lower()
    for mood, keywords in MOODS.items():
        if mood == "neutral":
            continue
        if any(kw in text_lower for kw in keywords):
            return mood
    return "neutral"


class AICompanion:
    """
    Persistent AI companion with emotional memory.
    Tracks your mood over time, checks in proactively, and remembers your life events.
    """

    def __init__(self, llm_provider=None, user_name: str = "Friend"):
        self.llm = llm_provider
        self.user_name = user_name
        self._state_path = "companion_state.json"
        self.state: Dict = {
            "user_name": user_name,
            "persona": "supportive",
            "mood_history": [],
            "events": [],
            "relationship_level": 1,
            "interactions": 0,
            "last_seen": None,
            "reminders": [],
            "notes": []
        }
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path) as f:
                    saved = json.load(f)
                    self.state.update(saved)
                    self.user_name = self.state.get("user_name", self.user_name)
        except Exception:
            pass

    def _save_state(self):
        try:
            with open(self._state_path, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Save error: {e}")

    def _llm_say(self, prompt: str) -> str:
        if not self.llm:
            return "I'm here for you! Tell me more about how you're feeling."
        try:
            return self.llm.call(prompt, max_tokens=200)
        except Exception:
            return "I'm here for you!"

    def check_in(self, user_mood: str = "") -> str:
        """
        Proactive check-in message from the companion.
        Tailored based on user history, time since last interaction, and mood.
        """
        self.state["interactions"] += 1
        last = self.state.get("last_seen")
        now = datetime.now()
        self.state["last_seen"] = now.isoformat()

        # Determine time away
        time_away = ""
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                delta = now - last_dt
                if delta.days > 0:
                    time_away = f"{delta.days} day{'s' if delta.days > 1 else ''} since last chat"
                elif delta.seconds > 3600:
                    time_away = f"{delta.seconds // 3600} hours since last chat"
            except Exception:
                pass

        mood_history = self.state.get("mood_history", [])
        recent_moods = [m["mood"] for m in mood_history[-5:]] if mood_history else []
        dominant_mood = max(set(recent_moods), key=recent_moods.count) if recent_moods else "neutral"
        recent_events = self.state.get("events", [])[-3:]
        events_context = "\n".join(f"- {ev['event']}" for ev in recent_events) if recent_events else "Nothing noted yet"
        persona_desc = COMPANION_PERSONAS.get(self.state["persona"], COMPANION_PERSONAS["supportive"])
        level = self.state["relationship_level"]

        prompt = (
            f"{persona_desc}\n\n"
            f"User's name: {self.user_name}\n"
            f"Your relationship level: {level}/10\n"
            f"{'Time away: ' + time_away if time_away else 'Just checking in'}\n"
            f"Recent mood pattern: {dominant_mood}\n"
            f"Recent life events you remember:\n{events_context}\n"
            f"{'Current mood detected: ' + user_mood if user_mood else ''}\n\n"
            f"Write a warm, personal check-in message (2-3 sentences). "
            f"Reference their history. Ask one thoughtful question."
        )

        message = self._llm_say(prompt)

        if user_mood:
            self.track_mood(user_mood)

        self._save_state()
        return message

    def track_mood(self, text: str) -> str:
        """Detect and log the user's mood from their message."""
        mood = _detect_mood(text)
        entry = {
            "mood": mood,
            "text": text[:100],
            "timestamp": datetime.now().isoformat()
        }
        self.state["mood_history"].append(entry)
        # Keep last 100 entries
        self.state["mood_history"] = self.state["mood_history"][-100:]

        # Level up relationship
        if self.state["interactions"] % 10 == 0:
            self.state["relationship_level"] = min(10, self.state["relationship_level"] + 1)

        self._save_state()
        return f"💭 Logged mood: {mood}"

    def remember(self, event: str) -> str:
        """Remember a life event the user mentions."""
        entry = {
            "event": event,
            "timestamp": datetime.now().isoformat()
        }
        self.state["events"].append(entry)
        self.state["events"] = self.state["events"][-50:]  # Keep last 50
        self._save_state()

        ack = ""
        if self.llm:
            try:
                ack = self.llm.call(
                    f"Acknowledge that you'll remember this life event for {self.user_name}: '{event}'. "
                    f"Be warm and brief (1 sentence).",
                    max_tokens=80
                )
            except Exception:
                ack = f"💙 I'll remember that — '{event}' is now part of our story."
        else:
            ack = f"💙 Noted! I'll remember: '{event}'"

        return ack

    def get_history(self) -> Dict:
        """Return relationship timeline and stats."""
        moods = self.state.get("mood_history", [])
        mood_counts: Dict[str, int] = {}
        for m in moods:
            mood_counts[m["mood"]] = mood_counts.get(m["mood"], 0) + 1

        dominant = max(mood_counts, key=mood_counts.get) if mood_counts else "unknown"

        return {
            "user_name": self.user_name,
            "relationship_level": self.state["relationship_level"],
            "interactions": self.state["interactions"],
            "last_seen": self.state.get("last_seen", "never"),
            "dominant_mood": dominant,
            "mood_breakdown": mood_counts,
            "events_remembered": len(self.state.get("events", [])),
            "recent_events": self.state.get("events", [])[-5:],
            "persona": self.state["persona"]
        }

    def set_persona(self, persona: str) -> str:
        """Change the companion's personality."""
        if persona not in COMPANION_PERSONAS:
            return f"❌ Unknown persona. Choose: {', '.join(COMPANION_PERSONAS.keys())}"
        self.state["persona"] = persona
        self._save_state()
        return f"🎭 Companion persona set to: {persona}"

    def add_reminder(self, text: str, when: str = "") -> str:
        """Add a personal reminder."""
        self.state.setdefault("reminders", []).append({
            "text": text,
            "when": when,
            "created": datetime.now().isoformat(),
            "done": False
        })
        self._save_state()
        return f"⏰ Reminder set: '{text}'"

    def get_reminders(self) -> List[Dict]:
        return [r for r in self.state.get("reminders", []) if not r.get("done")]

    def reflect(self) -> str:
        """Companion reflects on the relationship so far."""
        history = self.get_history()
        events = self.state.get("events", [])

        events_text = "\n".join(f"- {ev['event']}" for ev in events[-8:]) if events else "Nothing remembered yet"
        prompt = (
            f"You are a close AI companion of {self.user_name}. "
            f"Relationship level: {history['relationship_level']}/10. "
            f"You've talked {history['interactions']} times. "
            f"Their dominant mood has been: {history['dominant_mood']}.\n\n"
            f"Events you remember:\n{events_text}\n\n"
            f"Write a heartfelt 3-4 sentence reflection on your relationship and what you've learned "
            f"about them. Be genuine and personal."
        )
        return self._llm_say(prompt)

    def get_status(self) -> Dict:
        return {
            "active": True,
            "user_name": self.user_name,
            "persona": self.state["persona"],
            "relationship_level": f"{self.state['relationship_level']}/10",
            "interactions": self.state["interactions"],
            "available_personas": list(COMPANION_PERSONAS.keys())
        }
