"""
User Model Engine — Long-Term User Modeling (Phase 16)
=======================================================
Builds and persists a rich user profile that shapes every response.
Profile is stored in SQLite and injected into the system prompt.
"""

import json
import re
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional


DEFAULT_PROFILE = {
    "name": None,
    "profession": None,
    "expertise_areas": [],
    "goals": [],
    "communication_style": "balanced",  # concise / detailed / balanced
    "preferred_format": "prose",        # prose / bullet / code-first
    "timezone": None,
    "interests": [],
    "language": "en",
    "risk_appetite": "moderate",        # conservative / moderate / aggressive
    "custom": {},
    "interaction_count": 0,
    "last_seen": None,
    "created": datetime.now().isoformat(),
}

PROFILE_EXTRACTOR_SYSTEM = (
    "You are a user profile analyst. Given a conversation snippet, extract any new "
    "facts about the user. Return ONLY a JSON object with keys from this list "
    "(only include keys where you have new info): "
    "name, profession, expertise_areas, goals, communication_style, preferred_format, "
    "timezone, interests, language, risk_appetite. "
    "Values for list fields must be lists. Output valid JSON only."
)


class UserModelEngine:
    """
    Long-Term User Modeling — builds a persistent profile of user preferences,
    habits, and goals that shapes every agent response across sessions.
    """

    def __init__(self, database: Any, llm_provider: Any):
        self.db = database
        self.llm = llm_provider
        self.profile: Dict = DEFAULT_PROFILE.copy()
        self._dirty = False
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self):
        """Load profile from database if it exists."""
        try:
            raw = self.db.get_setting("user_profile_v2")
            if raw:
                saved = json.loads(raw)
                self.profile.update(saved)
        except Exception:
            pass  # First run — use defaults

    def save(self):
        """Persist the current profile to database."""
        try:
            self.db.set_setting("user_profile_v2", json.dumps(self.profile))
            self._dirty = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Profile Updates
    # ------------------------------------------------------------------
    def set(self, key: str, value: Any) -> str:
        """Manually set a profile field."""
        if key not in DEFAULT_PROFILE and key not in self.profile.get("custom", {}):
            self.profile.setdefault("custom", {})[key] = value
        else:
            # Handle list fields
            if isinstance(DEFAULT_PROFILE.get(key), list) and isinstance(value, str):
                existing = self.profile.get(key, [])
                if value not in existing:
                    existing.append(value)
                self.profile[key] = existing
            else:
                self.profile[key] = value
        self.profile["last_seen"] = datetime.now().isoformat()
        self._dirty = True
        self.save()
        return f"✅ Profile updated: {key} = {value}"

    def increment_interactions(self):
        """Call after each user interaction."""
        self.profile["interaction_count"] = self.profile.get("interaction_count", 0) + 1
        self.profile["last_seen"] = datetime.now().isoformat()
        self._dirty = True
        if self.profile["interaction_count"] % 10 == 0:
            self.save()  # Persist every 10 interactions

    async def update_from_conversation(
        self, user_input: str, agent_response: str, tenant_id: int = 1
    ):
        """Asynchronously extract and update profile facts from a conversation turn."""
        snippet = f"User said: {user_input[:400]}\nAgent said: {agent_response[:200]}"
        raw = await asyncio.to_thread(
            self.llm.call, snippet, system=PROFILE_EXTRACTOR_SYSTEM, history=[]
        )
        if not raw:
            return
        try:
            updates = json.loads(raw.strip()) if raw.strip().startswith("{") else {}
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            updates = json.loads(match.group()) if match else {}

        for key, val in updates.items():
            if key in self.profile:
                if isinstance(self.profile[key], list) and isinstance(val, list):
                    # Merge lists, dedup
                    merged = list(set(self.profile[key] + val))
                    self.profile[key] = merged
                elif isinstance(self.profile[key], list) and isinstance(val, str):
                    if val not in self.profile[key]:
                        self.profile[key].append(val)
                else:
                    self.profile[key] = val
        self._dirty = True

    def reset(self):
        """Reset profile to defaults."""
        self.profile = DEFAULT_PROFILE.copy()
        self.profile["created"] = datetime.now().isoformat()
        self.save()

    # ------------------------------------------------------------------
    # Prompt Injection
    # ------------------------------------------------------------------
    def build_system_inject(self) -> str:
        """Generate a system prompt snippet that personalizes the agent."""
        p = self.profile
        lines = ["[User Profile]"]
        if p.get("name"):
            lines.append(f"- User's name: {p['name']}")
        if p.get("profession"):
            lines.append(f"- Profession: {p['profession']}")
        if p.get("expertise_areas"):
            lines.append(f"- Expertise: {', '.join(p['expertise_areas'][:5])}")
        if p.get("goals"):
            lines.append(f"- Goals: {', '.join(p['goals'][:3])}")
        if p.get("communication_style"):
            lines.append(f"- Prefers {p['communication_style']} communication in {p.get('preferred_format', 'prose')} format.")
        if p.get("risk_appetite"):
            lines.append(f"- Risk appetite: {p['risk_appetite']}")
        if p.get("interests"):
            lines.append(f"- Interests: {', '.join(p['interests'][:5])}")
        return "\n".join(lines) if len(lines) > 1 else ""

    def show(self) -> str:
        """Pretty-print the user profile."""
        p = self.profile
        lines = [
            "┌─────────────────────────────────────┐",
            "│         LONG-TERM USER PROFILE      │",
            "└─────────────────────────────────────┘",
        ]
        for k, v in p.items():
            if v and v != [] and v != {}:
                lines.append(f"  {k:<25}: {v}")
        return "\n".join(lines)

    def describe(self) -> str:
        name = self.profile.get("name") or "Unknown"
        count = self.profile.get("interaction_count", 0)
        return f"UserModelEngine — User: {name}, {count} interactions tracked."
