"""
Persona Creator — design and save custom AI personalities.
Commands: /createpersona | /persona list|activate|delete|show <name>
"""

import os
import json
from datetime import datetime


class PersonaCreator:
    """Design, save, and activate custom AI personas."""

    DATA_FILE = "personas_data.json"

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "personas": {},
            "active": None,
            "defaults": {
                "Assistant": {
                    "name": "Assistant",
                    "description": "Default helpful assistant",
                    "traits": ["helpful", "precise", "friendly"],
                    "tone": "professional",
                    "system_prompt": "You are a helpful, precise, and friendly AI assistant.",
                    "created_at": "2026-01-01T00:00:00",
                    "built_in": True
                }
            }
        }

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def create_persona(self, name: str, description: str, traits: list,
                       tone: str, system_prompt: str = "") -> dict:
        """Create and save a new persona."""
        key = name.lower().replace(" ", "_")
        if not system_prompt:
            # Generate system prompt from traits
            system_prompt = self._generate_system_prompt(name, description, traits, tone)

        persona = {
            "name": name,
            "description": description,
            "traits": traits,
            "tone": tone,
            "system_prompt": system_prompt,
            "created_at": datetime.now().isoformat(),
            "built_in": False
        }
        self._data["personas"][key] = persona
        self._save()
        return {
            "success": True,
            "persona": persona,
            "message": (
                f"✅ Persona '{name}' created!\n"
                f"   🎭 Traits: {', '.join(traits)}\n"
                f"   🗣️ Tone: {tone}\n"
                f"   💬 Activate with: /persona activate {name}"
            )
        }

    def _generate_system_prompt(self, name: str, description: str, traits: list, tone: str) -> str:
        """Generate a system prompt from persona parameters."""
        if self.llm:
            try:
                prompt = (
                    f"Write a system prompt for an AI persona named '{name}'.\n"
                    f"Description: {description}\n"
                    f"Traits: {', '.join(traits)}\n"
                    f"Tone: {tone}\n"
                    "Write 3-5 sentences that define how this persona should communicate. "
                    "Be specific and vivid. Start with 'You are...'"
                )
                result = self.llm.chat(prompt)
                if result:
                    return result
            except Exception:
                pass
        # Fallback
        return (
            f"You are {name}, {description}. "
            f"Your personality traits are: {', '.join(traits)}. "
            f"Communicate in a {tone} tone at all times."
        )

    def activate(self, name: str) -> dict:
        """Set the active persona."""
        key = name.lower().replace(" ", "_")
        all_personas = {**self._data.get("defaults", {}), **self._data["personas"]}
        alt_keys = {k.lower().replace(" ", "_"): k for k in all_personas}

        if key in all_personas:
            persona = all_personas[key]
        elif key in alt_keys:
            persona = all_personas[alt_keys[key]]
        else:
            # Fuzzy
            matches = [k for k in all_personas if name.lower() in k.lower()]
            if matches:
                persona = all_personas[matches[0]]
            else:
                return {"success": False, "error": f"Persona '{name}' not found. Use /persona list to see all."}

        self._data["active"] = persona["name"]
        self._save()
        return {
            "success": True,
            "persona": persona,
            "system_prompt": persona["system_prompt"],
            "message": (
                f"🎭 Persona '{persona['name']}' activated!\n"
                f"   📝 {persona['description']}\n"
                f"   🗣️ Tone: {persona.get('tone', 'neutral')}\n"
                f"   ✨ The agent will now respond as this persona."
            )
        }

    def list_personas(self) -> str:
        """List all available personas."""
        all_personas = {**self._data.get("defaults", {}), **self._data["personas"]}
        active = self._data.get("active", "Assistant")
        if not all_personas:
            return "No personas found. Create one with /createpersona"
        lines = ["🎭 AVAILABLE PERSONAS:\n"]
        for key, p in all_personas.items():
            star = "★ " if p["name"] == active else "  "
            built = " [built-in]" if p.get("built_in") else ""
            traits = ", ".join(p.get("traits", []))
            lines.append(f"  {star}{p['name']}{built}")
            lines.append(f"     {p['description']}")
            lines.append(f"     Traits: {traits} | Tone: {p.get('tone', 'neutral')}")
            lines.append("")
        lines.append(f"  (★ = active persona)")
        return "\n".join(lines)

    def delete_persona(self, name: str) -> str:
        """Delete a custom persona."""
        key = name.lower().replace(" ", "_")
        if key in self._data["personas"]:
            del self._data["personas"][key]
            self._save()
            return f"🗑️ Persona '{name}' deleted."
        return f"❌ Custom persona '{name}' not found. Built-in personas cannot be deleted."

    def get_active_system_prompt(self) -> str:
        """Get the system prompt for the active persona."""
        active = self._data.get("active")
        if not active:
            return ""
        all_personas = {**self._data.get("defaults", {}), **self._data["personas"]}
        for k, p in all_personas.items():
            if p["name"] == active:
                return p.get("system_prompt", "")
        return ""

    def show_persona(self, name: str) -> str:
        """Show details of a specific persona."""
        key = name.lower().replace(" ", "_")
        all_personas = {**self._data.get("defaults", {}), **self._data["personas"]}
        for k, p in all_personas.items():
            if k == key or p["name"].lower() == name.lower():
                lines = [
                    f"🎭 PERSONA: {p['name']}",
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"Description : {p['description']}",
                    f"Traits      : {', '.join(p.get('traits', []))}",
                    f"Tone        : {p.get('tone', 'neutral')}",
                    f"Built-in    : {p.get('built_in', False)}",
                    f"Created     : {p.get('created_at', 'N/A')[:10]}",
                    f"\nSystem Prompt:\n{p.get('system_prompt', 'N/A')}"
                ]
                return "\n".join(lines)
        return f"Persona '{name}' not found."
