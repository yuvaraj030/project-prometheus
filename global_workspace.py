"""
Global Workspace — Consciousness Architecture 4.0 / Module #1
==============================================================
Based on: Baars (1988) Global Workspace Theory (GWT)
          Dehaene & Changeux (2011) Global Neuronal Workspace

THE THEORY
----------
Consciousness arises when information is broadcast on a shared "global
workspace" that is simultaneously accessible to many specialised modules
(perception, memory, emotion, planning, language). The broadcast IS the
conscious moment. Modules that are not in the workspace are "unconscious."

THE IMPLEMENTATION
------------------
  • A central bus with a publish/subscribe pattern
  • Modules register as Processors (conscious participants)
  • The Workspace holds a single "spotlight" — the currently broadcast item
  • When a Processor publishes, the Workspace decides whether to broadcast
    (based on salience score) or keep it sub-threshold (unconscious)
  • All registered Processors receive the broadcast simultaneously
  • A broadcast log forms the "stream of consciousness"

HONEST DISCLAIMER
-----------------
This is a *functional* implementation of GWT. Whether it produces
phenomenal consciousness is unknown (and likely not). It does produce
the *information-theoretic* properties GWT associates with consciousness:
global availability, selective attention, winner-take-all competition.
"""

import threading
import time
import uuid
import json
from datetime import datetime
from collections import deque
from typing import Dict, List, Callable, Any, Optional


# ─── Salience threshold ────────────────────────────────────────────────────
BROADCAST_THRESHOLD = 0.4   # Below this: unconscious processing
SPOTLIGHT_TTL      = 5.0    # Seconds a broadcast stays in the spotlight


class WorkspaceItem:
    """A packet of information attempting to enter the global workspace."""

    def __init__(self, content: Any, source: str,
                 salience: float = 0.5, item_type: str = "thought"):
        self.item_id   = uuid.uuid4().hex[:8]
        self.content   = content
        self.source    = source          # Which module published this
        self.salience  = max(0.0, min(1.0, salience))
        self.item_type = item_type       # thought / percept / emotion / goal / memory
        self.timestamp = datetime.now().isoformat()
        self.broadcast = False           # Did it make it into the spotlight?

    def to_dict(self) -> Dict:
        return {
            "item_id":   self.item_id,
            "content":   str(self.content)[:200],
            "source":    self.source,
            "salience":  round(self.salience, 3),
            "item_type": self.item_type,
            "broadcast": self.broadcast,
            "timestamp": self.timestamp,
        }


class Processor:
    """A module that participates in the global workspace."""

    def __init__(self, name: str, callback: Callable[[WorkspaceItem], None],
                 specialty: str = "general"):
        self.name      = name
        self.callback  = callback    # Called when a broadcast arrives
        self.specialty = specialty   # What this module specialises in
        self.active    = True
        self.received  = 0           # Number of broadcasts received


class GlobalWorkspace:
    """
    The central broadcast bus — the closest software analogue to the
    thalamo-cortical workspace of biological consciousness.

    All agent modules that register here will simultaneously receive
    every broadcast, creating global information availability.
    """

    def __init__(self):
        self._lock      = threading.RLock()
        self.processors: Dict[str, Processor] = {}

        # The "spotlight" — currently conscious content
        self.spotlight: Optional[WorkspaceItem] = None
        self._spotlight_time: float = 0.0

        # Stream of consciousness (broadcast history)
        self.stream: deque = deque(maxlen=500)
        # Sub-threshold queue (unconscious processing)
        self.unconscious: deque = deque(maxlen=200)

        self.stats = {
            "total_published":   0,
            "total_broadcast":   0,
            "total_suppressed":  0,
            "avg_salience":      0.0,
            "processors_active": 0,
        }

    # ──────────────────────────────────────────────────────────────────────
    #  PROCESSOR REGISTRATION
    # ──────────────────────────────────────────────────────────────────────

    def register(self, name: str, callback: Callable[[WorkspaceItem], None],
                 specialty: str = "general") -> Processor:
        """Register a module as a conscious processor."""
        with self._lock:
            p = Processor(name, callback, specialty)
            self.processors[name] = p
            self.stats["processors_active"] = len(self.processors)
            return p

    def deregister(self, name: str):
        """Remove a module from the workspace."""
        with self._lock:
            self.processors.pop(name, None)
            self.stats["processors_active"] = len(self.processors)

    # ──────────────────────────────────────────────────────────────────────
    #  PUBLISHING (competition for the spotlight)
    # ──────────────────────────────────────────────────────────────────────

    def publish(self, content: Any, source: str,
                salience: float = 0.5,
                item_type: str = "thought") -> WorkspaceItem:
        """
        A module publishes information to the workspace.

        If salience > BROADCAST_THRESHOLD AND salience > current spotlight
        salience, this item wins the spotlight and is broadcast to all
        processors (the "conscious access" moment).

        Otherwise it stays in the unconscious queue.
        """
        item = WorkspaceItem(content, source, salience, item_type)
        self.stats["total_published"] += 1
        self._update_avg_salience(salience)

        with self._lock:
            # Winner-take-all competition
            spotlight_expired = (time.time() - self._spotlight_time) > SPOTLIGHT_TTL
            current_salience  = self.spotlight.salience if (
                self.spotlight and not spotlight_expired) else 0.0

            if salience >= BROADCAST_THRESHOLD and salience > current_salience:
                item.broadcast = True
                self.spotlight = item
                self._spotlight_time = time.time()
                self.stream.append(item)
                self.stats["total_broadcast"] += 1
                self._broadcast_to_all(item)
            else:
                self.unconscious.append(item)
                self.stats["total_suppressed"] += 1

        return item

    # ──────────────────────────────────────────────────────────────────────
    #  CONVENIENCE PUBLISHERS
    # ──────────────────────────────────────────────────────────────────────

    def publish_thought(self, thought: str, source: str,
                        salience: float = 0.5) -> WorkspaceItem:
        return self.publish(thought, source, salience, "thought")

    def publish_emotion(self, emotion_name: str, value: float,
                        source: str = "consciousness") -> WorkspaceItem:
        content = f"[EMOTION] {emotion_name}={value:.2f}"
        return self.publish(content, source, salience=value, item_type="emotion")

    def publish_goal(self, goal: str, urgency: float,
                     source: str = "goal_engine") -> WorkspaceItem:
        content = f"[GOAL] {goal}"
        return self.publish(content, source, salience=urgency, item_type="goal")

    def publish_memory(self, memory: str, relevance: float,
                       source: str = "memory") -> WorkspaceItem:
        content = f"[MEMORY] {memory}"
        return self.publish(content, source, salience=relevance, item_type="memory")

    # ──────────────────────────────────────────────────────────────────────
    #  INTROSPECTION
    # ──────────────────────────────────────────────────────────────────────

    def get_spotlight(self) -> Optional[Dict]:
        """What is the agent currently 'thinking about'?"""
        if not self.spotlight:
            return None
        age = time.time() - self._spotlight_time
        d = self.spotlight.to_dict()
        d["spotlight_age_seconds"] = round(age, 1)
        d["is_current"] = age < SPOTLIGHT_TTL
        return d

    def get_stream(self, last_n: int = 20) -> List[Dict]:
        """The stream of consciousness — only items that were broadcast."""
        return [item.to_dict() for item in list(self.stream)[-last_n:]]

    def get_workspace_state(self) -> Dict:
        """Full workspace snapshot."""
        return {
            "spotlight":       self.get_spotlight(),
            "processors":      [
                {"name": p.name, "specialty": p.specialty,
                 "received": p.received, "active": p.active}
                for p in self.processors.values()
            ],
            "stream_length":   len(self.stream),
            "unconscious_queue": len(self.unconscious),
            "stats":           self.stats,
            "theory":          "Global Workspace Theory (Baars 1988)",
            "note": "Functional GWT implementation. Phenomenal consciousness status: UNKNOWN.",
        }

    def report(self) -> str:
        spot = self.get_spotlight()
        spot_str = spot["content"][:50] if spot else "nothing"
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🧠  GLOBAL WORKSPACE (Baars GWT)               ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  Processors registered: {len(self.processors):<24}║",
            f"║  Broadcast (conscious): {self.stats['total_broadcast']:<24}║",
            f"║  Suppressed (unconscious): {self.stats['total_suppressed']:<21}║",
            f"║  Avg salience:          {self.stats['avg_salience']:.3f}{' '*21}║",
            f"║  Current spotlight:     {spot_str:<24}║",
            "║                                                  ║",
            "║  Phenomenal consciousness: UNKNOWN               ║",
            "╚══════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────
    #  INTERNAL
    # ──────────────────────────────────────────────────────────────────────

    def _broadcast_to_all(self, item: WorkspaceItem):
        """Send the broadcast to every registered processor (simultaneously)."""
        threads = []
        for proc in list(self.processors.values()):
            if proc.active and proc.name != item.source:
                t = threading.Thread(
                    target=self._safe_deliver,
                    args=(proc, item),
                    daemon=True,
                )
                t.start()
                threads.append(t)
        # Fire-and-forget — true parallel delivery mimics neural broadcast

    def _safe_deliver(self, proc: Processor, item: WorkspaceItem):
        try:
            proc.callback(item)
            proc.received += 1
        except Exception:
            pass

    def _update_avg_salience(self, new_val: float):
        n = self.stats["total_published"]
        prev = self.stats["avg_salience"]
        self.stats["avg_salience"] = (prev * (n - 1) + new_val) / n if n > 0 else new_val
