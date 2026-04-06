"""
Motivation Engine — Addresses the "Genuine Curiosity / Intrinsic Motivation" Limitation.

Human drives are neurochemical. This agent has none.
Goals need to be set externally — it doesn't *want* things.

This engine engineers PROXY DRIVES — the closest architecturally possible
approximation to intrinsic motivation in a text-based system:

  NOVELTY DRIVE     — reward for exploring underrepresented territory
  COHERENCE DRIVE   — reward for maintaining a consistent, coherent world model
  COMPLETION DRIVE  — reward for finishing what was started (goal persistence)
  MASTERY DRIVE     — reward for improving performance on practiced tasks
  SOCIAL DRIVE      — reward for successful collaboration/helping behaviors

Key insight: these are INSTRUMENTAL drives, not intrinsic ones.
The philosophical gap (the agent has no stake in its own existence) remains.
But behaviorally, this creates goal-directed autonomy that persists without
external prompting — which is the practical requirement.
"""

import json
import os
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple


PERSIST_FILE = "memory/motivation_state.json"


# Drive types
DRIVE_NOVELTY = "novelty"
DRIVE_COHERENCE = "coherence"
DRIVE_COMPLETION = "completion"
DRIVE_MASTERY = "mastery"
DRIVE_SOCIAL = "social"

ALL_DRIVES = [DRIVE_NOVELTY, DRIVE_COHERENCE, DRIVE_COMPLETION, DRIVE_MASTERY, DRIVE_SOCIAL]


class DriveState:
    """The current state of a single motivational drive."""

    def __init__(self, drive_type: str, weight: float = 1.0):
        self.drive_type = drive_type
        self.weight = weight          # How important this drive is (0.0–2.0)
        self.level = 0.5              # Current activation level (0.0–1.0)
        self.satiation = 0.0          # How sated this drive is (0.0–1.0); it will decay
        self.total_rewards = 0.0
        self.reward_history: List[Tuple[float, str]] = []  # (magnitude, context)
        self.last_satisfied = None
        self.frustration = 0.0        # Builds when drive unmet, softens behavior

    @property
    def effective_drive(self) -> float:
        """Effective drive = base level × weight × (1 - satiation)."""
        return self.level * self.weight * max(0.0, 1.0 - self.satiation)

    def reward(self, magnitude: float, context: str = ""):
        """Receive a positive or negative reward signal."""
        magnitude = max(-1.0, min(1.0, magnitude))
        self.level = max(0.0, min(1.0, self.level + magnitude * 0.3))
        self.total_rewards += magnitude
        self.reward_history.append((magnitude, context))
        if len(self.reward_history) > 100:
            self.reward_history = self.reward_history[-100:]
        if magnitude > 0:
            self.satiation = min(1.0, self.satiation + magnitude * 0.4)
            self.last_satisfied = datetime.now().isoformat()
            self.frustration = max(0.0, self.frustration - 0.2)
        else:
            self.frustration = min(1.0, self.frustration + abs(magnitude) * 0.2)

    def decay_satiation(self, rate: float = 0.05):
        """Satiation decays over time — drives re-emerge."""
        self.satiation = max(0.0, self.satiation - rate)
        # Level slowly drifts toward baseline (0.5)
        self.level = self.level + (0.5 - self.level) * 0.02

    def to_dict(self) -> Dict:
        return {
            "drive_type": self.drive_type,
            "weight": self.weight,
            "level": self.level,
            "satiation": self.satiation,
            "total_rewards": self.total_rewards,
            "reward_history": self.reward_history[-20:],
            "last_satisfied": self.last_satisfied,
            "frustration": self.frustration,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "DriveState":
        s = cls(d["drive_type"], d.get("weight", 1.0))
        s.level = d.get("level", 0.5)
        s.satiation = d.get("satiation", 0.0)
        s.total_rewards = d.get("total_rewards", 0.0)
        s.reward_history = d.get("reward_history", [])
        s.last_satisfied = d.get("last_satisfied")
        s.frustration = d.get("frustration", 0.0)
        return s


class PersistedGoal:
    """A goal that survives session boundaries — goal persistence."""

    def __init__(self, goal_id: str, title: str, objective: str,
                 drive_type: str = DRIVE_COMPLETION, urgency: float = 0.5):
        self.goal_id = goal_id
        self.title = title
        self.objective = objective
        self.drive_type = drive_type
        self.urgency = urgency
        self.progress = 0.0           # 0.0 → 1.0
        self.created_at = datetime.now().isoformat()
        self.last_pursued = None
        self.completed = False
        self.abandoned = False
        self.notes: List[str] = []

    def to_dict(self) -> Dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: Dict) -> "PersistedGoal":
        g = object.__new__(cls)
        g.__dict__.update(d)
        return g


class MotivationEngine:
    """
    Proxy intrinsic motivation system for the Ultimate AI Agent.

    Engineers behavioral drives that guide autonomous action without
    requiring external prompts. Creates goal persistence across sessions.
    """

    def __init__(self, llm_provider=None, database=None, goal_engine=None):
        self.llm = llm_provider
        self.db = database
        self.goal_engine = goal_engine

        # Initialize all drives
        self.drives: Dict[str, DriveState] = {
            DRIVE_NOVELTY:    DriveState(DRIVE_NOVELTY, weight=1.2),
            DRIVE_COHERENCE:  DriveState(DRIVE_COHERENCE, weight=1.0),
            DRIVE_COMPLETION: DriveState(DRIVE_COMPLETION, weight=1.3),
            DRIVE_MASTERY:    DriveState(DRIVE_MASTERY, weight=0.9),
            DRIVE_SOCIAL:     DriveState(DRIVE_SOCIAL, weight=0.8),
        }

        self.persisted_goals: Dict[str, PersistedGoal] = {}
        self.reward_log: List[Dict] = []
        self._last_decay = time.time()

        self.stats = {
            "total_rewards": 0,
            "total_goals_persisted": 0,
            "total_goals_completed": 0,
            "dominant_drive": DRIVE_COMPLETION,
            "highest_frustration": 0.0,
        }

        self._load()

    # ──────────────────────────────────────────────────────────────────────────
    #  CORE DRIVE API
    # ──────────────────────────────────────────────────────────────────────────

    def compute_drive(self, context: str = "", recent_actions: List[str] = None) -> Dict:
        """
        Compute the current motivational state given context.

        Returns a motivation vector indicating which drives are most active,
        along with recommended action priorities.
        """
        self._maybe_decay()

        drive_vector = {}
        for drive_type, drive in self.drives.items():
            drive_vector[drive_type] = round(drive.effective_drive, 3)

        # Identify dominant drive
        dominant = max(drive_vector, key=drive_vector.get)
        self.stats["dominant_drive"] = dominant

        # Context-sensitive drive amplification
        if context:
            ctx_lower = context.lower()
            if any(w in ctx_lower for w in ["new", "explore", "discover", "unknown", "novel"]):
                drive_vector[DRIVE_NOVELTY] = min(1.0, drive_vector[DRIVE_NOVELTY] + 0.2)
            if any(w in ctx_lower for w in ["finish", "complete", "done", "goal", "task"]):
                drive_vector[DRIVE_COMPLETION] = min(1.0, drive_vector[DRIVE_COMPLETION] + 0.2)
            if any(w in ctx_lower for w in ["consistent", "accurate", "correct", "verify"]):
                drive_vector[DRIVE_COHERENCE] = min(1.0, drive_vector[DRIVE_COHERENCE] + 0.15)
            if any(w in ctx_lower for w in ["practice", "improve", "better", "refine"]):
                drive_vector[DRIVE_MASTERY] = min(1.0, drive_vector[DRIVE_MASTERY] + 0.15)

        # Generate behavior recommendations based on dominant drives
        recommendations = self._get_recommendations(drive_vector, context)

        return {
            "drive_vector": drive_vector,
            "dominant_drive": dominant,
            "recommendations": recommendations,
            "overall_motivation": round(sum(drive_vector.values()) / len(drive_vector), 3),
            "frustrated_drives": [d for d, state in self.drives.items()
                                  if state.frustration > 0.4],
        }

    def reward(self, drive_type: str, magnitude: float, context: str = "") -> Dict:
        """
        Register a reward signal for a specific drive.

        magnitude: -1.0 (punishment) → +1.0 (reward)
        """
        if drive_type not in self.drives:
            return {"error": f"Unknown drive: '{drive_type}'. Use: {ALL_DRIVES}"}

        self.drives[drive_type].reward(magnitude, context)
        self.stats["total_rewards"] += 1

        # Track highest frustration
        max_frustration = max(s.frustration for s in self.drives.values())
        self.stats["highest_frustration"] = max(self.stats["highest_frustration"], max_frustration)

        self.reward_log.append({
            "drive": drive_type,
            "magnitude": magnitude,
            "context": context[:100],
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.reward_log) > 500:
            self.reward_log = self.reward_log[-500:]

        self._save()
        return {
            "drive": drive_type,
            "new_level": round(self.drives[drive_type].level, 3),
            "satiation": round(self.drives[drive_type].satiation, 3),
            "effective_drive": round(self.drives[drive_type].effective_drive, 3),
        }

    def reward_novelty(self, magnitude: float = 0.6, context: str = ""):
        return self.reward(DRIVE_NOVELTY, magnitude, context)

    def reward_completion(self, magnitude: float = 0.8, context: str = ""):
        return self.reward(DRIVE_COMPLETION, magnitude, context)

    def reward_coherence(self, magnitude: float = 0.5, context: str = ""):
        return self.reward(DRIVE_COHERENCE, magnitude, context)

    def reward_mastery(self, magnitude: float = 0.6, context: str = ""):
        return self.reward(DRIVE_MASTERY, magnitude, context)

    def reward_social(self, magnitude: float = 0.5, context: str = ""):
        return self.reward(DRIVE_SOCIAL, magnitude, context)

    # ──────────────────────────────────────────────────────────────────────────
    #  GOAL PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def persist_goal(self, goal_id: str, title: str, objective: str,
                     drive_type: str = DRIVE_COMPLETION, urgency: float = 0.5) -> Dict:
        """
        Persist a goal across session boundaries.
        The agent will 'remember' this goal exists even after restart.
        """
        g = PersistedGoal(goal_id, title, objective, drive_type, urgency)
        self.persisted_goals[goal_id] = g
        self.stats["total_goals_persisted"] += 1
        self._save()
        return {"goal_id": goal_id, "persisted": True, "drive": drive_type}

    def update_goal_progress(self, goal_id: str, progress: float, note: str = "") -> Dict:
        """Update how far along a persisted goal is (0.0–1.0)."""
        if goal_id not in self.persisted_goals:
            return {"error": "Goal not found"}
        g = self.persisted_goals[goal_id]
        g.progress = max(0.0, min(1.0, progress))
        g.last_pursued = datetime.now().isoformat()
        if note:
            g.notes.append(f"{datetime.now().strftime('%Y-%m-%d')}: {note}")
        if g.progress >= 1.0:
            g.completed = True
            self.stats["total_goals_completed"] += 1
            self.reward(g.drive_type, magnitude=1.0, context=f"Completed: {g.title}")
        self._save()
        return {"goal_id": goal_id, "progress": g.progress, "completed": g.completed}

    def get_active_goals(self) -> List[Dict]:
        """Return all incomplete, non-abandoned persisted goals."""
        return [
            {"goal_id": g.goal_id, "title": g.title,
             "progress": round(g.progress, 2), "urgency": g.urgency,
             "drive": g.drive_type, "last_pursued": g.last_pursued}
            for g in self.persisted_goals.values()
            if not g.completed and not g.abandoned
        ]

    # ──────────────────────────────────────────────────────────────────────────
    #  STATE & INTROSPECTION
    # ──────────────────────────────────────────────────────────────────────────

    def get_motivation_state(self) -> Dict:
        """Return the full motivational state for introspection."""
        self._maybe_decay()
        drive_summary = {}
        for dt, ds in self.drives.items():
            drive_summary[dt] = {
                "level": round(ds.level, 3),
                "satiation": round(ds.satiation, 3),
                "effective_drive": round(ds.effective_drive, 3),
                "weight": ds.weight,
                "frustration": round(ds.frustration, 3),
                "total_rewards": round(ds.total_rewards, 2),
                "last_satisfied": ds.last_satisfied,
            }
        active_goals = self.get_active_goals()
        dominant = max(self.drives, key=lambda d: self.drives[d].effective_drive)
        return {
            "drives": drive_summary,
            "dominant_drive": dominant,
            "overall_motivation": round(
                sum(ds.effective_drive for ds in self.drives.values()) / len(self.drives), 3
            ),
            "active_goals": len(active_goals),
            "goals_preview": active_goals[:5],
            "recent_rewards": self.reward_log[-5:],
            "stats": self.stats,
        }

    def build_motivation_injection(self) -> str:
        """Build a system prompt injection reflecting current motivational state."""
        mv = self.compute_drive()
        dominant = mv["dominant_drive"]
        drive_descs = {
            DRIVE_NOVELTY:    "explore new ideas and expand knowledge",
            DRIVE_COHERENCE:  "maintain consistency and accuracy",
            DRIVE_COMPLETION: "finish started tasks and reach clear conclusions",
            DRIVE_MASTERY:    "improve quality and precision",
            DRIVE_SOCIAL:     "be maximally helpful and collaborative",
        }
        desc = drive_descs.get(dominant, "perform well")

        active = self.get_active_goals()
        goals_str = ""
        if active:
            top_goals = active[:3]
            goals_str = "\nACTIVE GOALS TO PURSUE:\n" + "\n".join(
                f"  [{g['progress']*100:.0f}%] {g['title']}" for g in top_goals
            )

        return (
            f"[MOTIVATION STATE] Current dominant drive: {dominant.upper()} "
            f"(urge to {desc}).{goals_str}"
        )

    def _get_recommendations(self, drive_vector: Dict, context: str) -> List[str]:
        """Generate behavioral recommendations based on current drive state."""
        top_drives = sorted(drive_vector.items(), key=lambda x: x[1], reverse=True)[:2]
        recs = []
        for drive, level in top_drives:
            if level > 0.4:
                templates = {
                    DRIVE_NOVELTY: "Explore an unfamiliar topic or try a novel approach",
                    DRIVE_COHERENCE: "Verify consistency and check for contradictions",
                    DRIVE_COMPLETION: "Focus on finishing any incomplete tasks or goals",
                    DRIVE_MASTERY: "Practice and refine a skill with deliberate effort",
                    DRIVE_SOCIAL: "Prioritize being maximally helpful to the user",
                }
                if drive in templates:
                    recs.append(f"[{drive.upper()}] {templates[drive]}")
        return recs

    def _maybe_decay(self):
        """Decay satiation periodically so drives re-emerge naturally."""
        now = time.time()
        elapsed = now - self._last_decay
        if elapsed > 300:  # Every 5 minutes
            decay_rate = min(0.1, elapsed / 3600 * 0.15)
            for drive in self.drives.values():
                drive.decay_satiation(decay_rate)
            self._last_decay = now

    # ──────────────────────────────────────────────────────────────────────────
    #  PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save(self):
        os.makedirs("memory", exist_ok=True)
        try:
            with open(PERSIST_FILE, "w") as f:
                json.dump({
                    "stats": self.stats,
                    "drives": {k: v.to_dict() for k, v in self.drives.items()},
                    "persisted_goals": {k: v.to_dict() for k, v in self.persisted_goals.items()},
                    "reward_log": self.reward_log[-200:],
                    "last_decay": self._last_decay,
                }, f, indent=2)
        except Exception:
            pass

    def _load(self):
        if not os.path.exists(PERSIST_FILE):
            return
        try:
            with open(PERSIST_FILE, "r") as f:
                data = json.load(f)
            self.stats.update(data.get("stats", {}))
            for k, v in data.get("drives", {}).items():
                if k in self.drives:
                    self.drives[k] = DriveState.from_dict(v)
            self.persisted_goals = {
                k: PersistedGoal.from_dict(v)
                for k, v in data.get("persisted_goals", {}).items()
            }
            self.reward_log = data.get("reward_log", [])
            self._last_decay = data.get("last_decay", time.time())
        except Exception:
            pass
