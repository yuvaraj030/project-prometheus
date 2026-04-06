"""
Habit Tracker — daily habits, streaks, and AI pep-talks.
Commands: /habit add|done|list|streak|remove|stats
"""

import json
import os
from datetime import datetime, date, timedelta


class HabitTracker:
    """Track daily habits with streak counting and AI motivation."""

    DATA_FILE = "habit_data.json"

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._data = self._load()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"habits": {}, "completions": {}}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    # ── Core API ─────────────────────────────────────────────────────────────

    def add_habit(self, name: str, description: str = "", frequency: str = "daily"):
        """Add a new habit to track."""
        key = name.lower().replace(" ", "_")
        if key in self._data["habits"]:
            return f"⚠️ Habit '{name}' already exists."
        self._data["habits"][key] = {
            "name": name,
            "description": description,
            "frequency": frequency,
            "created": date.today().isoformat()
        }
        self._save()
        return f"✅ Habit '{name}' added! Complete it daily with: /habit done {name}"

    def remove_habit(self, name: str):
        """Remove a habit."""
        key = name.lower().replace(" ", "_")
        if key not in self._data["habits"]:
            return f"❌ Habit '{name}' not found."
        del self._data["habits"][key]
        self._save()
        return f"🗑️ Habit '{name}' removed."

    def mark_done(self, name: str):
        """Mark a habit as completed today."""
        key = name.lower().replace(" ", "_")
        if key not in self._data["habits"]:
            # Try fuzzy match
            matches = [k for k in self._data["habits"] if name.lower() in k]
            if matches:
                key = matches[0]
            else:
                return f"❌ Habit '{name}' not found. Use /habit list to see habits."

        today = date.today().isoformat()
        if key not in self._data["completions"]:
            self._data["completions"][key] = []

        if today in self._data["completions"][key]:
            return f"✅ '{self._data['habits'][key]['name']}' already done today! Keep it up! 🔥"

        self._data["completions"][key].append(today)
        self._data["completions"][key] = sorted(self._data["completions"][key])[-365:]  # keep 1 year
        self._save()

        streak = self._get_streak(key)
        pep_talk = self._generate_pep_talk(self._data["habits"][key]["name"], streak)
        return (
            f"🎉 '{self._data['habits'][key]['name']}' marked done!\n"
            f"   🔥 Streak: {streak} day{'s' if streak != 1 else ''}\n"
            f"   💬 {pep_talk}"
        )

    def list_habits(self):
        """List all habits with today's completion status."""
        if not self._data["habits"]:
            return "No habits tracked yet. Add one with: /habit add <name>"

        today = date.today().isoformat()
        lines = ["📋 YOUR HABITS:\n"]
        for key, habit in self._data["habits"].items():
            completions = self._data["completions"].get(key, [])
            done_today = today in completions
            streak = self._get_streak(key)
            status = "✅" if done_today else "⬜"
            lines.append(
                f"  {status} {habit['name']}"
                f"  |  🔥 {streak}d streak"
                f"{'  [DONE TODAY]' if done_today else ''}"
            )
        return "\n".join(lines)

    def get_streaks(self):
        """Return streak report for all habits."""
        if not self._data["habits"]:
            return "No habits tracked yet."
        lines = ["🔥 HABIT STREAKS:\n"]
        sorted_habits = sorted(
            self._data["habits"].items(),
            key=lambda x: self._get_streak(x[0]),
            reverse=True
        )
        for key, habit in sorted_habits:
            streak = self._get_streak(key)
            best = self._get_best_streak(key)
            total = len(self._data["completions"].get(key, []))
            bar = "█" * min(streak, 20) + "░" * max(0, 20 - streak)
            lines.append(f"  {habit['name']}")
            lines.append(f"    [{bar}] {streak}d current | {best}d best | {total} total")
        return "\n".join(lines)

    def get_stats(self):
        """Full statistics."""
        total_habits = len(self._data["habits"])
        today = date.today().isoformat()
        done_today = sum(
            1 for k in self._data["habits"]
            if today in self._data["completions"].get(k, [])
        )
        streaks = {k: self._get_streak(k) for k in self._data["habits"]}
        best_streak_habit = max(streaks, key=streaks.get) if streaks else None

        return {
            "total_habits": total_habits,
            "done_today": done_today,
            "completion_today_pct": round(done_today / total_habits * 100) if total_habits else 0,
            "best_current_streak": {
                "habit": self._data["habits"][best_streak_habit]["name"] if best_streak_habit else None,
                "days": streaks.get(best_streak_habit, 0)
            }
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_streak(self, key: str) -> int:
        """Calculate current streak for a habit."""
        completions = set(self._data["completions"].get(key, []))
        if not completions:
            return 0
        streak = 0
        check = date.today()
        while check.isoformat() in completions:
            streak += 1
            check -= timedelta(days=1)
        # Also check yesterday (if not done today yet, streak not broken)
        if date.today().isoformat() not in completions:
            check = date.today() - timedelta(days=1)
            while check.isoformat() in completions:
                streak += 1
                check -= timedelta(days=1)
        return streak

    def _get_best_streak(self, key: str) -> int:
        """Calculate best ever streak."""
        completions = sorted(self._data["completions"].get(key, []))
        if not completions:
            return 0
        best = cur = 1
        for i in range(1, len(completions)):
            d1 = date.fromisoformat(completions[i-1])
            d2 = date.fromisoformat(completions[i])
            if (d2 - d1).days == 1:
                cur += 1
                best = max(best, cur)
            else:
                cur = 1
        return best

    def _generate_pep_talk(self, habit_name: str, streak: int) -> str:
        """LLM or fallback pep talk."""
        milestones = {1: "First step! The journey of 1000 miles begins! 🚶",
                      3: "3-day streak! You're building a real habit! 💪",
                      7: "One week! You're in the top 20% of people who stick to habits! 🌟",
                      14: "Two weeks! This is becoming automatic. Your brain is rewiring! 🧠",
                      21: "21 days! Science says this is where habits are born! 🎯",
                      30: "30 DAYS! You're a habit champion! 🏆",
                      50: "50 DAYS! Legendary consistency! 🌈",
                      100: "100 DAYS! You're in the 1%! UNSTOPPABLE! 🚀"}
        if streak in milestones:
            return milestones[streak]
        if not self.llm:
            return f"Day {streak} — keep the momentum! Every day counts! 🔥"
        try:
            prompt = (
                f"User completed '{habit_name}' for day {streak} in a row. "
                "Give ONE short motivational sentence (max 15 words). Be specific and energetic."
            )
            return self.llm.chat(prompt, system="You are an enthusiastic habit coach.") or f"Day {streak} — amazing! 🔥"
        except Exception:
            return f"Day {streak} — keep the fire alive! 🔥"
