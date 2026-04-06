"""
Life RPG — Gamify your life with XP, levels, skills, and quests.
Commands: /rpg status|xp|quest|level|skills|leaderboard
Syncs with habit_tracker.py for automatic XP rewards.
"""

import os
import json
import math
from datetime import datetime


class LifeRPG:
    """Gamify real life — earn XP for habits, skills, and completed goals."""

    DATA_FILE = "rpg_data.json"

    # XP needed to level up: XP = level * 100
    SKILLS = ["Mental", "Physical", "Social", "Creative", "Technical", "Financial", "Wisdom"]

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
            "player": {
                "name": "Hero",
                "class": "Apprentice",
                "level": 1,
                "xp": 0,
                "total_xp": 0,
                "coins": 0,
                "created_at": datetime.now().isoformat()
            },
            "skills": {s: {"level": 1, "xp": 0} for s in self.SKILLS},
            "quests": [],
            "completed_quests": [],
            "achievements": [],
            "inventory": []
        }

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def _xp_to_next_level(self, level: int) -> int:
        return level * 100

    def _add_xp(self, amount: int, skill: str = None) -> list:
        """Add XP and handle level ups."""
        events = []
        self._data["player"]["xp"] += amount
        self._data["player"]["total_xp"] += amount

        # Check player level up
        while True:
            needed = self._xp_to_next_level(self._data["player"]["level"])
            if self._data["player"]["xp"] >= needed:
                self._data["player"]["xp"] -= needed
                self._data["player"]["level"] += 1
                self._data["player"]["coins"] += 10
                new_level = self._data["player"]["level"]
                events.append(f"🎉 LEVEL UP! You are now Level {new_level}! +10 coins!")
                self._update_class(new_level)
                events.append(f"🏅 Class: {self._data['player']['class']}")
            else:
                break

        # Skill XP
        if skill and skill.title() in self._data["skills"]:
            sk = skill.title()
            self._data["skills"][sk]["xp"] += amount
            while True:
                sk_needed = self._xp_to_next_level(self._data["skills"][sk]["level"])
                if self._data["skills"][sk]["xp"] >= sk_needed:
                    self._data["skills"][sk]["xp"] -= sk_needed
                    self._data["skills"][sk]["level"] += 1
                    events.append(f"⬆️ {sk} skill leveled up to {self._data['skills'][sk]['level']}!")
                else:
                    break

        self._save()
        return events

    def _update_class(self, level: int):
        classes = {1: "Apprentice", 5: "Journeyman", 10: "Adept",
                   20: "Expert", 35: "Master", 50: "Grandmaster", 75: "Legend", 100: "Mythic"}
        for threshold in sorted(classes.keys(), reverse=True):
            if level >= threshold:
                self._data["player"]["class"] = classes[threshold]
                break

    def earn_xp(self, skill: str, amount: int, reason: str = "") -> str:
        """Earn XP in a skill."""
        amount = max(1, min(amount, 1000))
        events = self._add_xp(amount, skill)
        sk_display = skill.title() if skill.title() in self._data["skills"] else "General"

        lines = [
            f"✨ +{amount} XP earned in {sk_display}!",
            f"   Reason: {reason}" if reason else "",
            f"   Player Level: {self._data['player']['level']} ({self._data['player']['xp']}/{self._xp_to_next_level(self._data['player']['level'])} XP)"
        ]
        lines += [f"   {e}" for e in events]
        return "\n".join(l for l in lines if l)

    def get_status(self) -> str:
        """Full RPG status display."""
        p = self._data["player"]
        needed = self._xp_to_next_level(p["level"])
        progress = int((p["xp"] / needed) * 20)
        bar = "█" * progress + "░" * (20 - progress)

        active_quests = [q for q in self._data["quests"] if not q.get("completed")]
        lines = [
            f"⚔️  LIFE RPG — {p['name']}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  Class : {p['class']}",
            f"  Level : {p['level']}",
            f"  XP    : [{bar}] {p['xp']}/{needed}",
            f"  Total : {p['total_xp']} XP  |  💰 {p['coins']} coins",
            f"",
            f"  SKILLS:"
        ]
        for skill, data in self._data["skills"].items():
            sk_bar = "▮" * min(data["level"], 10) + "▯" * max(0, 10 - data["level"])
            lines.append(f"    {skill:<12} Lv.{data['level']:>2} [{sk_bar}]")
        lines.append(f"")
        lines.append(f"  ⚔️  Active Quests: {len(active_quests)}")
        for q in active_quests[:3]:
            lines.append(f"    • {q['name']} [+{q.get('xp_reward', 50)} XP]")
        lines.append(f"  🏆 Completed: {len(self._data['completed_quests'])} quests")
        return "\n".join(lines)

    def add_quest(self, name: str, description: str = "", xp_reward: int = 50, skill: str = "General") -> str:
        """Add a new quest."""
        quest = {
            "id": len(self._data["quests"]) + len(self._data["completed_quests"]) + 1,
            "name": name,
            "description": description,
            "xp_reward": xp_reward,
            "skill": skill,
            "created_at": datetime.now().isoformat(),
            "completed": False
        }
        self._data["quests"].append(quest)
        self._save()
        return f"⚔️ Quest added: '{name}'\n   Reward: +{xp_reward} XP | Skill: {skill}\n   Complete with: /rpg quest complete {name}"

    def complete_quest(self, name: str) -> str:
        """Mark a quest as complete and award XP."""
        for quest in self._data["quests"]:
            if quest["name"].lower() == name.lower() and not quest.get("completed"):
                quest["completed"] = True
                quest["completed_at"] = datetime.now().isoformat()
                self._data["completed_quests"].append(quest)
                self._data["quests"].remove(quest)
                events = self._add_xp(quest.get("xp_reward", 50), quest.get("skill"))
                lines = [
                    f"🎉 QUEST COMPLETE: '{quest['name']}'!",
                    f"   +{quest.get('xp_reward', 50)} XP rewarded!",
                ] + [f"   {e}" for e in events]
                self._save()
                return "\n".join(lines)
        return f"Quest '{name}' not found or already completed."

    def list_quests(self, show_completed: bool = False) -> str:
        """List quests."""
        quests = self._data["completed_quests"][-5:] if show_completed else self._data["quests"]
        label = "COMPLETED QUESTS" if show_completed else "ACTIVE QUESTS"
        if not quests:
            return f"No {'completed' if show_completed else 'active'} quests. Add one with /rpg quest add <name>"
        lines = [f"⚔️  {label}:\n"]
        for q in quests:
            icon = "✅" if show_completed else "🗡️"
            lines.append(f"  {icon} [{q['id']}] {q['name']} (+{q.get('xp_reward', 50)} XP)")
            if q.get("description"):
                lines.append(f"      {q['description']}")
        return "\n".join(lines)

    def set_player_name(self, name: str) -> str:
        """Set player name."""
        self._data["player"]["name"] = name
        self._save()
        return f"⚔️ Player name set to: {name}"
