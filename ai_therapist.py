"""
AI Therapist — CBT-style journaling + emotional pattern tracking.
Commands: /therapy journal|analyze|history|tips|mood
"""

import os
import json
from datetime import datetime, date


class AITherapist:
    """CBT-style journaling with emotional pattern analysis."""

    DATA_FILE = "therapy_data.json"

    SYSTEM_PROMPT = (
        "You are a compassionate, evidence-based AI therapist trained in Cognitive Behavioral Therapy (CBT). "
        "You help users identify thought patterns, cognitive distortions, and emotional triggers. "
        "You NEVER diagnose or replace a real therapist. Always remind users to seek professional help for serious issues. "
        "Respond with warmth, empathy, and concrete CBT techniques."
    )

    EMOTIONS = ["happy", "sad", "anxious", "angry", "frustrated", "grateful", "excited",
                "lonely", "stressed", "calm", "confused", "hopeful", "overwhelmed", "proud"]

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
        return {"entries": [], "patterns": {}, "total_entries": 0}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def journal(self, text: str) -> dict:
        """Add a journal entry and get CBT-style response."""
        if not text.strip():
            return {"success": False, "error": "Please share what's on your mind."}

        # Detect emotion keywords
        detected_emotions = [e for e in self.EMOTIONS if e in text.lower()]

        entry = {
            "id": self._data["total_entries"] + 1,
            "text": text,
            "emotions": detected_emotions,
            "date": datetime.now().isoformat(),
            "response": ""
        }

        # Get LLM response
        if self.llm:
            try:
                prompt = (
                    f"The user has shared this journal entry:\n\n\"{text}\"\n\n"
                    "Provide a therapeutic CBT response that:\n"
                    "1. Validates their feelings\n"
                    "2. Identifies any cognitive distortions (if present)\n"
                    "3. Suggests one practical CBT exercise or reframe\n"
                    "4. Ends with an encouraging question to promote reflection\n\n"
                    "Keep it warm, concise (4-6 sentences), and practical."
                )
                response = self.llm.chat(prompt, system=self.SYSTEM_PROMPT) or ""
                entry["response"] = response
            except Exception as e:
                entry["response"] = "Thank you for sharing. Be gentle with yourself. Feelings are not facts."

        # Track emotion patterns
        for emotion in detected_emotions:
            self._data["patterns"][emotion] = self._data["patterns"].get(emotion, 0) + 1

        self._data["entries"].append(entry)
        self._data["entries"] = self._data["entries"][-200:]  # keep 200
        self._data["total_entries"] += 1
        self._save()

        return {
            "success": True,
            "emotions": detected_emotions,
            "response": entry["response"],
            "entry_id": entry["id"]
        }

    def analyze_patterns(self) -> str:
        """Analyze emotional patterns from journal history."""
        if not self._data["entries"]:
            return "No journal entries yet. Start with /therapy journal <your thoughts>"

        # Frequency analysis
        patterns = self._data["patterns"]
        if not patterns:
            return "Journal more to see patterns emerge!"

        sorted_emotions = sorted(patterns.items(), key=lambda x: -x[1])
        top_emotions = sorted_emotions[:5]

        # LLM analysis
        analysis = ""
        if self.llm and len(self._data["entries"]) >= 3:
            recent = self._data["entries"][-5:]
            texts = "\n".join(f"- {e['text'][:200]}" for e in recent)
            try:
                prompt = (
                    f"Analyze these recent journal entries:\n{texts}\n\n"
                    "In 3-4 sentences, identify:\n"
                    "1. The main emotional theme\n"
                    "2. Any recurring cognitive pattern\n"
                    "3. One strength you observe\n"
                    "Be warm, specific, and insightful."
                )
                analysis = self.llm.chat(prompt, system=self.SYSTEM_PROMPT) or ""
            except Exception:
                pass

        lines = [
            f"🧠 EMOTIONAL PATTERN ANALYSIS",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Total Entries: {self._data['total_entries']}",
            f"",
            f"Top Emotions:",
        ]
        for emotion, count in top_emotions:
            bar = "█" * min(count, 15)
            lines.append(f"  {emotion:<14} {bar} ({count}x)")

        if analysis:
            lines.append(f"\n🔍 AI Insights:\n{analysis}")

        lines.append(f"\n💡 Tip: /therapy tips to get CBT exercises")
        return "\n".join(lines)

    def get_history(self, limit: int = 5) -> str:
        """Show recent journal entries."""
        if not self._data["entries"]:
            return "No entries yet. /therapy journal <your thoughts>"
        lines = [f"📖 JOURNAL HISTORY (last {limit} entries):\n"]
        for entry in reversed(self._data["entries"][-limit:]):
            dt = entry["date"][:10]
            emo_str = f" [{', '.join(entry['emotions'][:3])}]" if entry.get("emotions") else ""
            lines.append(f"  [{entry['id']}] {dt}{emo_str}")
            lines.append(f"     📝 {entry['text'][:120]}...")
            if entry.get("response"):
                lines.append(f"     💬 {entry['response'][:120]}...")
            lines.append("")
        return "\n".join(lines)

    def get_tips(self, situation: str = "") -> str:
        """Get CBT tips and exercises."""
        if not self.llm:
            tips = [
                "🌬️ Box Breathing: Inhale 4s → Hold 4s → Exhale 4s → Hold 4s. Repeat 4x.",
                "📝 Thought Record: Write the situation → your thought → the emotion → evidence for/against.",
                "⚡ 5-4-3-2-1 Grounding: Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste.",
                "🔄 Cognitive Reframe: Ask 'Is this thought 100% true? What would I tell a friend in this situation?'",
                "🎯 Behavioral Activation: Do ONE small enjoyable activity today, even if you don't feel like it."
            ]
            return "💡 CBT TECHNIQUES:\n\n" + "\n\n".join(tips)
        try:
            prompt = (
                f"Give 3 specific CBT exercises for: '{situation if situation else 'general stress and anxiety'}'\n"
                "For each, give: name, brief explanation, and exact steps. Be practical and clear."
            )
            result = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            return f"💡 CBT TECHNIQUES for '{situation or 'general wellness'}':\n\n{result}"
        except Exception:
            return "Consider: journaling, box breathing, or the 5-4-3-2-1 grounding technique. 🌿"
