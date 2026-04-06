"""
Music Composer — LLM generates chord progressions, melodies, and song lyrics.
Commands: /compose [mood/genre]|/compose lyrics <theme>|/compose chords <key>|/compose song <title>
"""

import os
import json
from datetime import datetime


class MusicComposer:
    """Generate musical compositions: chord progressions, melodies, and lyrics via LLM."""

    DATA_FILE = "music_data.json"

    SYSTEM_PROMPT = (
        "You are a world-class music composer and songwriter with expertise in music theory, "
        "chord progressions, melody writing, and lyric crafting. You write in ABC notation for melodies "
        "and standard chord symbols (Am, G, F, C, etc.) for progressions. Be specific and musical."
    )

    MOODS = {
        "happy": "C major, upbeat, energetic",
        "sad": "A minor, slow, melancholic",
        "epic": "D minor, orchestral, powerful",
        "jazz": "Bb major, swing, sophisticated",
        "romantic": "G major, gentle, flowing",
        "chill": "F major, Lo-fi, relaxed",
        "angry": "B minor, heavy, intense",
        "mysterious": "E minor, atmospheric, eerie"
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
        return {"compositions": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def compose_full_song(self, mood: str = "happy", title: str = "") -> dict:
        """Generate a full song: structure, chords, and lyrics."""
        if not self.llm:
            return {"success": False, "error": "LLM required for composition."}

        mood_desc = self.MOODS.get(mood.lower(), mood)
        prompt = f"""Compose a complete song with mood: {mood} ({mood_desc})

Create a full song with this structure:

## 🎵 SONG: {title or f'Untitled {mood.title()} Song'}

### 🎹 KEY & TEMPO
Key: [Key signature]
Tempo: [BPM] BPM ([feel description])
Time Signature: [e.g., 4/4]

### 🎸 CHORD PROGRESSIONS
**Verse:**
| Chord | Duration | Chord | Duration |
(Show 8 bars in table format)

**Chorus:**
| Chord | Duration | Chord | Duration |
(Show 4 bars — the hook)

**Bridge:**
| Chord | Duration | Chord | Duration |

### 🎶 MELODY (ABC Notation)
```abc
X:1
T:{title or 'Untitled'}
M:4/4
K:{mood_desc.split(',')[0]}
[Write 8 bars of melody in ABC notation]
```

### 📝 LYRICS

**[Verse 1]**
[4 lines, rhyming ABAB]

**[Pre-Chorus]**
[2 lines building tension]

**[Chorus]**
[4 lines — the emotional core, memorable, repeatable]

**[Verse 2]**
[4 new lines, different imagery]

**[Bridge]**
[4 lines — emotional peak or twist]

**[Outro]**
[2 lines — resolution]

### 🎯 PRODUCTION NOTES
[Brief description of instrumentation, feel, and reference artists]
"""
        try:
            result = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            if not result:
                return {"success": False, "error": "LLM returned empty response."}

            composition = {
                "id": len(self._data["compositions"]) + 1,
                "title": title or f"Untitled {mood.title()} Song",
                "mood": mood,
                "content": result,
                "created_at": datetime.now().isoformat()
            }
            self._data["compositions"].append(composition)
            self._data["compositions"] = self._data["compositions"][-50:]
            self._save()
            return {"success": True, "composition": result, "id": composition["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def compose_chords(self, key: str = "C major", style: str = "pop") -> dict:
        """Generate just a chord progression."""
        if not self.llm:
            return {"success": False, "error": "LLM required."}
        prompt = (
            f"Generate a creative chord progression in {key} for {style} music.\n"
            "Include:\n"
            "1. Main progression (8 bars with Roman numerals AND chord names)\n"
            "2. Variation (4 bars)\n"
            "3. Bridge progression (4 bars)\n"
            "4. Voice leading tips for guitar and piano\n"
            "5. Similar songs using this progression\n\n"
            "Format clearly with labels and examples."
        )
        try:
            result = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            return {"success": True, "content": result or "No result."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def compose_lyrics(self, theme: str, style: str = "pop") -> dict:
        """Generate lyrics for a given theme."""
        if not self.llm:
            return {"success": False, "error": "LLM required."}
        prompt = (
            f"Write a complete set of {style} song lyrics about: '{theme}'\n\n"
            "Include: Verse 1, Pre-Chorus, Chorus (x2), Verse 2, Bridge, Final Chorus, Outro\n"
            "Make the chorus highly memorable and emotionally resonant. "
            "Use vivid metaphors and specific imagery. Avoid clichés."
        )
        try:
            result = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            return {"success": True, "lyrics": result or "No result."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_compositions(self) -> str:
        """List saved compositions."""
        if not self._data["compositions"]:
            return "No compositions yet. Use /compose <mood> to create one."
        lines = ["🎵 COMPOSITIONS:\n"]
        for c in reversed(self._data["compositions"][-10:]):
            lines.append(f"  [{c['id']}] {c['title']} | Mood: {c['mood']} | {c['created_at'][:10]}")
        return "\n".join(lines)

    def get_mood_list(self) -> str:
        """List available moods."""
        lines = ["🎹 AVAILABLE MOODS:\n"]
        for mood, desc in self.MOODS.items():
            lines.append(f"  • {mood:<12} — {desc}")
        lines.append("\nUsage: /compose <mood>  or  /compose lyrics <theme>  or  /compose chords <key>")
        return "\n".join(lines)
