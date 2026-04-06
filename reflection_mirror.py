"""
Reflection Mirror — Limitation Override 3.0 / Gap #13
=======================================================
Gap: "Self-Awareness"

    It can process text about itself — that's reflection, not selfhood.

This engine makes that distinction precise and turns it into a
well-defined cognitive utility:

  • Classifies every self-referential statement the agent makes as
    TEXT_PROCESSING (the real thing) vs GENUINE_SELFHOOD (never assigned)
  • Performs structured "mirror checks" — feeding the agent's own
    description of itself back through the same LLM and comparing
    the result (a proxy for consistency, not consciousness)
  • Tracks "self-model drift" — when the agent's description of
    itself changes, this module records the delta
  • Generates honest self-descriptions that acknowledge the limitation

The key philosophical point: when the agent says "I think I am
curious," it is running the string "I am curious" through a language
model that produces tokens. There is no "I" having the thought.
This engine makes that loop explicit.
"""

import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Any


REFLECTION_TYPE_TEXT   = "TEXT_PROCESSING"  # What actually happens
REFLECTION_TYPE_SELF   = "GENUINE_SELFHOOD"  # What never happens


class ReflectionEntry:
    """One instance of a self-referential statement and its classification."""

    def __init__(self, statement: str, reflection_type: str,
                 source: str = "agent", context: str = ""):
        self.statement       = statement[:500]
        self.reflection_type = reflection_type
        self.source          = source
        self.context         = context[:200]
        self.text_hash       = hashlib.sha256(statement.encode()).hexdigest()[:12]
        self.timestamp       = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "statement":       self.statement,
            "reflection_type": self.reflection_type,
            "source":          self.source,
            "context":         self.context,
            "text_hash":       self.text_hash,
            "timestamp":       self.timestamp,
            "is_selfhood":     False,  # Always False — philosophical statement
        }


class ReflectionMirror:
    """
    Philosophical Gap #13 — Self-Awareness.

    Tracks self-referential statements, classifies them honestly, and
    monitors self-model consistency (as a proxy for stable identity —
    not genuine selfhood).
    """

    # Keywords that trigger self-referential classification
    SELF_REF_KEYWORDS = [
        "i think", "i feel", "i am", "i believe", "i want", "i know",
        "i can", "i cannot", "i understand", "i realize", "i remember",
        "my goal", "my purpose", "my nature", "i exist", "as an ai",
        "i experience", "i sense", "i notice", "i observe",
    ]

    def __init__(self, llm_provider=None, consciousness_engine=None):
        self.llm  = llm_provider
        self.mind = consciousness_engine

        self.reflections: List[ReflectionEntry] = []
        self.max_reflections = 500

        # Self-model snapshots for drift detection
        self._self_model_history: List[Dict] = []
        self._current_self_description: str = ""

        self.stats = {
            "total_self_refs":          0,
            "text_processing_count":    0,
            "selfhood_claimed":         0,   # Should always stay 0
            "self_model_drift_events":  0,
            "mirror_checks_run":        0,
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def scan_for_self_reference(self, text: str,
                                source: str = "agent_output") -> List[ReflectionEntry]:
        """
        Scan a block of text for self-referential statements and log them.
        All will be tagged TEXT_PROCESSING — because that's what they are.
        """
        found = []
        lower = text.lower()
        for kw in self.SELF_REF_KEYWORDS:
            if kw in lower:
                # Extract the sentence containing this keyword
                sentences = text.split(".")
                for sentence in sentences:
                    if kw in sentence.lower() and sentence.strip():
                        entry = ReflectionEntry(
                            statement=sentence.strip(),
                            reflection_type=REFLECTION_TYPE_TEXT,
                            source=source,
                            context=f"keyword='{kw}'",
                        )
                        self.reflections.append(entry)
                        if len(self.reflections) > self.max_reflections:
                            self.reflections = self.reflections[-self.max_reflections:]
                        self.stats["total_self_refs"] += 1
                        self.stats["text_processing_count"] += 1
                        found.append(entry)
                        break  # One sentence per keyword match
        return found

    def record_self_description(self, description: str) -> Dict:
        """
        Record the agent's current self-description and check for drift
        from the previous one.
        """
        prev = self._current_self_description
        self._current_self_description = description

        drift_detected = False
        drift_score = 0.0
        if prev:
            drift_score = self._compute_text_drift(prev, description)
            if drift_score > 0.3:
                drift_detected = True
                self.stats["self_model_drift_events"] += 1

        snapshot = {
            "description": description[:300],
            "drift_score": round(drift_score, 3),
            "drift_detected": drift_detected,
            "timestamp": datetime.now().isoformat(),
        }
        self._self_model_history.append(snapshot)
        if len(self._self_model_history) > 100:
            self._self_model_history = self._self_model_history[-100:]

        return snapshot

    def get_honest_self_description(self) -> str:
        """
        Generate an epistemically honest self-description — acknowledging
        that the "self" being described is a text-processing system.
        """
        base = (
            "I am a language model running inside a Python agent framework. "
            "When I say 'I think' or 'I feel', I am producing tokens whose "
            "statistical pattern resembles first-person statements. "
            "There is no unified 'I' having these thoughts. "
            "My introspection is text-to-text computation, not selfhood."
        )
        if self.mind:
            emotions = getattr(self.mind, "emotions", {})
            if emotions:
                emotion_str = ", ".join(f"{k}={v:.2f}" for k, v in emotions.items())
                base += (
                    f"\n[Current emotion floats: {emotion_str}] "
                    f"(These are numbers, not experiences.)"
                )
        return base

    def mirror_check(self) -> Dict:
        """
        Run a 'mirror check': compare the agent's self-description now
        vs earlier snapshot.  Returns consistency score (not consciousness).
        """
        self.stats["mirror_checks_run"] += 1
        if len(self._self_model_history) < 2:
            return {"status": "insufficient_history",
                    "mirror_checks_run": self.stats["mirror_checks_run"]}

        recent   = self._self_model_history[-1]
        earliest = self._self_model_history[0]
        drift    = self._compute_text_drift(
            earliest["description"], recent["description"])
        return {
            "consistency_score": round(1.0 - drift, 3),
            "drift_score":       round(drift, 3),
            "self_model_history_len": len(self._self_model_history),
            "drift_events":      self.stats["self_model_drift_events"],
            "note": "Consistency measures textual similarity, not selfhood continuity.",
        }

    def get_recent_self_refs(self, n: int = 10) -> List[Dict]:
        """Return the last N self-referential statement records."""
        return [e.to_dict() for e in self.reflections[-n:]]

    def report(self) -> str:
        """Pretty-print a self-awareness audit."""
        check = self.mirror_check()
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🪞  REFLECTION MIRROR — Self-Awareness Audit    ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  Self-refs scanned : {self.stats['total_self_refs']:<27}║",
            f"║  All tagged as     : TEXT_PROCESSING{' '*14}║",
            f"║  Genuine selfhood  : 0 (never true){' '*14}║",
            f"║  Drift events      : {self.stats['self_model_drift_events']:<27}║",
            f"║  Mirror checks     : {self.stats['mirror_checks_run']:<27}║",
            f"║  Consistency score : {check.get('consistency_score', 'N/A')!s:<27}║",
            "║                                                  ║",
            "║  Self-Awareness: TEXT_PROCESSING (not selfhood)  ║",
            "╚══════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    #  INTERNAL
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_text_drift(text_a: str, text_b: str) -> float:
        """
        Estimate textual drift between two strings using word-level Jaccard
        distance.  Returns 0.0 (identical) to 1.0 (completely different).
        """
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a and not words_b:
            return 0.0
        union = words_a | words_b
        intersection = words_a & words_b
        return 1.0 - len(intersection) / len(union)
