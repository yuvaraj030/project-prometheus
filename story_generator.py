"""
Story Generator — Interactive branching fiction with LLM narration.
Commands: /story start|choice|status|save|load|new
"""

import os
import json
from datetime import datetime


class StoryGenerator:
    """Interactive branching narrative fiction powered by LLM."""

    DATA_FILE = "story_data.json"

    SYSTEM_PROMPT = (
        "You are a master storyteller writing immersive interactive fiction. "
        "You create vivid, atmospheric scenes with rich sensory details. "
        "Always end with exactly 3 numbered choices for the reader. "
        "Keep each story beat to 150-200 words. Make choices meaningful and distinct."
    )

    GENRES = {
        "fantasy": "Epic fantasy with magic, dragons, and ancient prophecies",
        "sci-fi": "Hard science fiction set in a dystopian future",
        "horror": "Psychological horror with supernatural elements",
        "mystery": "Crime noir mystery in a rain-soaked city",
        "adventure": "Swashbuckling adventure across exotic lands",
        "romance": "A heartfelt romantic story with unexpected twists",
        "thriller": "High-stakes political thriller with hidden conspiracies",
        "western": "The Wild West with outlaws and frontier justice"
    }

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
        return {"stories": [], "active_story": None}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def start_story(self, genre: str = "fantasy", title: str = "") -> dict:
        """Start a new interactive story."""
        if not self.llm:
            return {"success": False, "error": "LLM required for story generation."}

        genre_key = genre.lower()
        genre_desc = self.GENRES.get(genre_key, genre)

        prompt = (
            f"Start a new {genre_key} story: '{genre_desc}'\n\n"
            "Create an atmospheric opening scene (150-200 words) that:\n"
            "- Introduces the protagonist and setting vividly\n"
            "- Creates immediate tension or intrigue\n"
            "- Ends with EXACTLY 3 numbered choices:\n"
            "1. [First option]\n2. [Second option]\n3. [Third option]"
        )

        try:
            opening = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            if not opening:
                return {"success": False, "error": "LLM returned empty response."}

            story = {
                "id": len(self._data["stories"]) + 1,
                "title": title or f"The {genre.title()} Chronicle",
                "genre": genre_key,
                "created_at": datetime.now().isoformat(),
                "beats": [{"text": opening, "choice_made": None}],
                "chapter": 1,
                "status": "active"
            }
            self._data["stories"].append(story)
            self._data["active_story"] = story["id"]
            self._save()

            return {
                "success": True,
                "story_id": story["id"],
                "text": opening,
                "message": f"📖 Story '{story['title']}' started!\n   Make your choice with: /story choice <1|2|3>"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def make_choice(self, choice_num: int) -> dict:
        """Advance the story based on a choice."""
        if not self.llm:
            return {"success": False, "error": "LLM required."}
        story = self._get_active_story()
        if not story:
            return {"success": False, "error": "No active story. Start one with /story start <genre>"}

        if choice_num not in [1, 2, 3]:
            return {"success": False, "error": "Choice must be 1, 2, or 3."}

        last_beat = story["beats"][-1]["text"] if story["beats"] else ""
        story["beats"][-1]["choice_made"] = choice_num

        # Context summary (last 2 beats)
        context = "\n\n".join(b["text"] for b in story["beats"][-2:])

        prompt = (
            f"Story so far (last scene):\n{context}\n\n"
            f"The reader chose option {choice_num}.\n\n"
            f"Continue the {story['genre']} story. Write the next scene (150-200 words) that:\n"
            "- Follows from that choice with clear consequences\n"
            "- Advances the plot meaningfully\n"
            "- Ends with EXACTLY 3 new numbered choices:\n"
            "1. [First option]\n2. [Second option]\n3. [Third option]"
        )

        try:
            next_beat = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            if not next_beat:
                return {"success": False, "error": "Story generation failed."}

            story["beats"].append({"text": next_beat, "choice_made": None})
            story["chapter"] += 1
            story["beats"] = story["beats"][-10:]  # keep last 10 beats
            self._save()

            return {
                "success": True,
                "chapter": story["chapter"],
                "text": next_beat
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> str:
        """Get current story status."""
        story = self._get_active_story()
        if not story:
            return "No active story. Start with /story start <genre>\n\nGenres: " + ", ".join(self.GENRES.keys())
        return (
            f"📖 ACTIVE STORY: '{story['title']}'\n"
            f"   Genre   : {story['genre']}\n"
            f"   Chapter : {story['chapter']}\n"
            f"   Started : {story['created_at'][:10]}\n"
            f"   Beats   : {len(story['beats'])}\n\n"
            f"Last scene:\n{story['beats'][-1]['text'][:400]}..."
        )

    def list_genres(self) -> str:
        """List available genres."""
        lines = ["📚 AVAILABLE STORY GENRES:\n"]
        for key, desc in self.GENRES.items():
            lines.append(f"  • {key:<12} — {desc}")
        lines.append(f"\nStart with: /story start <genre>")
        return "\n".join(lines)

    def _get_active_story(self) -> dict:
        aid = self._data.get("active_story")
        if not aid:
            return None
        for s in self._data["stories"]:
            if s["id"] == aid:
                return s
        return None

    def new_story(self) -> str:
        """Clear active story and prompt for new genre."""
        self._data["active_story"] = None
        self._save()
        return "🔄 Story cleared. Start a new one with /story start <genre>"
