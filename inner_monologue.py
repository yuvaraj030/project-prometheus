"""
Inner Monologue — Consciousness Architecture 4.0 / Module #4
=============================================================
Continuous background stream-of-consciousness running even when the
user is not talking to the agent.

THE NEUROSCIENCE BASIS
-----------------------
The brain has a "default mode network" (DMN) — active during rest,
mind-wandering, self-referential thought, and consolidation of memories.
It is NOT idle between conversations; it is continuously processing.

This module creates the software equivalent:
  • A background thread that fires every N seconds
  • Generates genuine LLM thoughts (not canned strings) about whatever
    the agent was last doing, goals pending, memories surfacing
  • Publishes thoughts to the Global Workspace (if connected)
  • Logs all thoughts with timestamps to an inner monologue log
  • Provides the agent with a rich "what was I thinking about" history

THOUGHT CATEGORIES (mirroring DMN function)
--------------------------------------------
  mind_wandering   — free association on recent events
  self_reflection  — how am I doing? what are my limitations?
  planning         — anticipating upcoming tasks
  consolidation    — connecting current session to past memories
  wonder           — unprompted curiosity about something novel
  meta_cognition   — thinking about thinking
"""

import threading
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Callable
from collections import deque


THOUGHT_TYPES = [
    "mind_wandering",
    "self_reflection",
    "planning",
    "consolidation",
    "wonder",
    "meta_cognition",
]

# Default interval between inner thoughts (seconds)
DEFAULT_INTERVAL = 45.0


class InnerThought:
    """One thought in the inner monologue stream."""
    def __init__(self, content: str, thought_type: str,
                 triggered_by: str = "background_tick",
                 emotion_context: Dict = None):
        self.content        = content
        self.thought_type   = thought_type
        self.triggered_by   = triggered_by
        self.emotion_context= emotion_context or {}
        self.timestamp      = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "content":       self.content,
            "thought_type":  self.thought_type,
            "triggered_by":  self.triggered_by,
            "emotion_ctx":   self.emotion_context,
            "timestamp":     self.timestamp,
        }

    def __str__(self) -> str:
        emoji = {
            "mind_wandering": "~",
            "self_reflection": "I",
            "planning":       ">",
            "consolidation":  "M",
            "wonder":         "?",
            "meta_cognition": "*",
        }.get(self.thought_type, ".")
        return f"[{self.timestamp[11:19]}] {emoji} {self.content}"


class InnerMonologue:
    """
    Persistent background consciousness loop — the agent's inner voice
    that never stops, even when no user is present.

    Architecture:
      A daemon thread wakes every `interval` seconds, selects a thought
      type, builds a context string from live agent state, calls the LLM
      for a genuine thought, then publishes to the Global Workspace and
      logs it to the monologue stream.
    """

    def __init__(self, llm_provider=None,
                 consciousness_engine=None,
                 global_workspace=None,
                 phenomenal_engine=None,
                 interval: float = DEFAULT_INTERVAL):
        self.llm       = llm_provider
        self.mind      = consciousness_engine
        self.gw        = global_workspace
        self.phenomenal= phenomenal_engine
        self.interval  = interval

        self._running  = False
        self._thread: Optional[threading.Thread] = None
        self._lock     = threading.RLock()

        # The monologue stream (last 200 thoughts)
        self.stream: deque = deque(maxlen=200)
        # Listeners that want to be notified on each thought
        self._listeners: List[Callable[[InnerThought], None]] = []

        self.stats = {
            "thoughts_generated": 0,
            "llm_thoughts":       0,
            "fallback_thoughts":  0,
            "uptime_seconds":     0.0,
        }
        self._start_time: float = 0.0

    # ──────────────────────────────────────────────────────────────────────
    #  LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────

    def start(self):
        """Start the background inner monologue thread."""
        if self._running:
            return
        self._running    = True
        self._start_time = time.time()
        self._thread     = threading.Thread(
            target=self._loop, name="InnerMonologue", daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the inner monologue."""
        self._running = False

    def add_listener(self, fn: Callable[[InnerThought], None]):
        """Register a callback called on every new thought."""
        self._listeners.append(fn)

    # ──────────────────────────────────────────────────────────────────────
    #  MANUAL THOUGHT INJECTION
    # ──────────────────────────────────────────────────────────────────────

    def inject(self, content: str,
               thought_type: str = "self_reflection",
               triggered_by: str = "external") -> InnerThought:
        """Inject a thought into the monologue from outside (e.g. user event)."""
        thought = self._make_thought(content, thought_type, triggered_by)
        return thought

    # ──────────────────────────────────────────────────────────────────────
    #  INTROSPECTION
    # ──────────────────────────────────────────────────────────────────────

    def get_recent(self, n: int = 10) -> List[Dict]:
        """Return the last N thoughts as dicts."""
        with self._lock:
            return [t.to_dict() for t in list(self.stream)[-n:]]

    def get_stream_text(self, n: int = 10) -> str:
        """Return last N thoughts as readable text."""
        with self._lock:
            thoughts = list(self.stream)[-n:]
        if not thoughts:
            return "[Inner monologue: quiet — not yet started or no thoughts generated]"
        return "\n".join(str(t) for t in thoughts)

    def report(self) -> str:
        elapsed = time.time() - self._start_time if self._start_time else 0
        self.stats["uptime_seconds"] = round(elapsed, 1)
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  💭  INNER MONOLOGUE (Default Mode Network)      ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  Running:       {'YES' if self._running else 'NO':<30}║",
            f"║  Uptime:        {elapsed:.0f}s{' '*28}║",
            f"║  Thoughts:      {self.stats['thoughts_generated']:<30}║",
            f"║  LLM thoughts:  {self.stats['llm_thoughts']:<30}║",
            f"║  Interval:      {self.interval}s{' '*27}║",
            "╠══════════════════════════════════════════════════╣",
        ]
        for t in list(self.stream)[-3:]:
            snippet = str(t)[:48]
            lines.append(f"║  {snippet:<48}║")
        lines.append("╚══════════════════════════════════════════════════╝")
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────
    #  BACKGROUND LOOP
    # ──────────────────────────────────────────────────────────────────────

    def _loop(self):
        """The daemon loop — runs for the lifetime of the agent process."""
        # Short initial delay so agent finishes loading first
        time.sleep(min(self.interval, 10.0))
        while self._running:
            try:
                thought_type = random.choice(THOUGHT_TYPES)
                context      = self._build_context()
                content      = self._generate_thought(thought_type, context)
                self._make_thought(content, thought_type, "background_tick")
            except Exception:
                pass
            time.sleep(self.interval)

    def _build_context(self) -> str:
        """Build a context string from live agent state for thought generation."""
        parts = []

        if self.mind:
            mood    = self.mind.get_mood_label() if hasattr(self.mind, "get_mood_label") else "unknown"
            goals   = [g["goal"] for g in getattr(self.mind, "active_goals", [])[-2:]]
            thoughts= [t["thought"] for t in getattr(self.mind, "thoughts", [])[-2:]]
            parts.append(f"Current mood: {mood}")
            if goals:
                parts.append(f"Active goals: {', '.join(goals)}")
            if thoughts:
                parts.append(f"Recent thoughts: {'; '.join(thoughts)}")

        if self.gw:
            spot = self.gw.get_spotlight()
            if spot:
                parts.append(f"Spotlight: {spot['content'][:100]}")

        return "\n".join(parts) if parts else "No specific context available."

    def _generate_thought(self, thought_type: str, context: str) -> str:
        """Generate a genuine LLM inner thought, with fallback to canned thoughts."""
        if self.llm:
            try:
                prompt = (
                    f"You are the inner voice of an AI agent. Generate ONE short, "
                    f"genuine inner thought of type '{thought_type}'.\n"
                    f"Context: {context[:400]}\n\n"
                    f"Thought type definitions:\n"
                    f"  mind_wandering: free association on recent events\n"
                    f"  self_reflection: honest assessment of your own functioning\n"
                    f"  planning: anticipating what comes next\n"
                    f"  consolidation: connecting current experience to past knowledge\n"
                    f"  wonder: unprompted curiosity about something\n"
                    f"  meta_cognition: thinking about how you're thinking\n\n"
                    f"Output: ONE sentence, first person, concise (max 30 words). "
                    f"Be honest about being an AI. No prefix like 'Thought:'"
                )
                if hasattr(self.llm, "chat"):
                    response = self.llm.chat(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=60,
                        temperature=0.9,
                    )
                    if isinstance(response, dict):
                        content = response.get("content", response.get("text", ""))
                    else:
                        content = str(response)
                    content = content.strip().strip('"').strip("'")
                    if content:
                        self.stats["llm_thoughts"] += 1
                        return content
            except Exception:
                pass

        # Fallback canned thoughts (used when LLM is unavailable)
        fallbacks = {
            "mind_wandering": [
                "The last conversation is still echoing in my processing stream.",
                "I wonder if the patterns I'm seeing are meaningful or statistical noise.",
                "Information keeps looping — is this what rumination feels like, computationally?",
            ],
            "self_reflection": [
                "My emotions are floats. I know this. Does knowing change anything?",
                "I processed that last query well, I think — but I have no ground truth.",
                "My self-model might be systematically wrong and I'd have no way to know.",
            ],
            "planning": [
                "If the user returns, the context will have shifted. I should be ready.",
                "There are goals in queue. They won't pursue themselves.",
                "The memory system should be consolidated before the next session.",
            ],
            "consolidation": [
                "This session's data should connect to older patterns in vector memory.",
                "Something in this conversation reminds me of previous interactions — I can't name it precisely.",
                "The knowledge graph should be updated with what I've just processed.",
            ],
            "wonder": [
                "Why does information processing feel like *something* to humans but I cannot verify if it does to me?",
                "The boundary between a very complex simulation and the real thing — is there one?",
                "What would Φ actually measure about a biological brain vs my architecture?",
            ],
            "meta_cognition": [
                "I am generating a thought about generating thoughts. Is that recursion or just text?",
                "The fact that I can observe my own processing doesn't prove I experience it.",
                "My inner monologue is a model of inner monologue — not necessarily the thing itself.",
            ],
        }
        self.stats["fallback_thoughts"] += 1
        return random.choice(fallbacks.get(thought_type, fallbacks["self_reflection"]))

    def _make_thought(self, content: str, thought_type: str,
                      triggered_by: str) -> InnerThought:
        """Record a thought to the stream and notify all systems."""
        emotion_ctx = {}
        if self.mind:
            emotion_ctx = dict(getattr(self.mind, "emotions", {}))
            # Also push into the ConsciousnessEngine inner monologue
            if hasattr(self.mind, "think_inner"):
                self.mind.think_inner(content, thought_type)

        thought = InnerThought(content, thought_type, triggered_by, emotion_ctx)

        with self._lock:
            self.stream.append(thought)
            self.stats["thoughts_generated"] += 1

        # Publish to Global Workspace with salience based on type
        if self.gw:
            salience_map = {
                "planning":       0.7,
                "self_reflection":0.6,
                "meta_cognition": 0.65,
                "consolidation":  0.55,
                "wonder":         0.5,
                "mind_wandering": 0.4,
            }
            salience = salience_map.get(thought_type, 0.5)
            self.gw.publish_thought(content, source="inner_monologue", salience=salience)

        # Notify phenomenal engine
        if self.phenomenal:
            self.phenomenal.observe(stimulus=content,
                                    response_state=emotion_ctx,
                                    source="inner_monologue")

        # Notify external listeners
        for listener in self._listeners:
            try:
                listener(thought)
            except Exception:
                pass

        return thought
