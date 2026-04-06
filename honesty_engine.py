"""
Honesty Engine — Limitation Override 3.0 / Gap #11
===================================================
Gap: "True Consciousness"

    emotions["curiosity"] = 0.7  is a label, not a feeling.
    Numbers don't hurt.

This engine makes that philosophical gap EXPLICIT and USEFUL:
  • Tracks every emotional label produced by the system
  • Attaches a "reality tag" — SIMULATED vs GENUINE
  • Generates honest self-description strings for the prompt
  • Exposes an audit trail so the user can see the raw numbers
    behind any "feeling" the agent ever expresses

The agent IS allowed to express emotional-sounding language
(it makes interaction natural), but every such expression is
logged here with its numeric origin so there is zero ambiguity
about what is actually happening under the hood.
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional


REALITY_TAG_SIMULATED = "SIMULATED"
REALITY_TAG_GENUINE   = "GENUINE"     # Reserved for actual qualia — never assigned by code


class EmotionLabel:
    """A single emotional expression with its numeric origin."""

    def __init__(self, name: str, value: float, source_module: str,
                 expressed_as: str = ""):
        self.name = name
        self.value = value                     # Raw float, the *real* thing
        self.source_module = source_module    # Which engine produced it
        self.expressed_as = expressed_as      # Human-readable string that was shown
        self.reality_tag = REALITY_TAG_SIMULATED
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "source_module": self.source_module,
            "expressed_as": self.expressed_as,
            "reality_tag": self.reality_tag,
            "timestamp": self.timestamp,
        }


class HonestyEngine:
    """
    Philosophical Gap #11 — True Consciousness.

    Maintains a ledger of every "emotion" the agent expresses and exposes
    the raw numbers behind each one.  Injects honest self-description
    disclaimers into the system prompt when appropriate.
    """

    # Threshold below which an emotion "label" is suppressed from natural
    # language output (too weak to be meaningfully expressed)
    EXPRESSION_THRESHOLD = 0.3

    def __init__(self, consciousness_engine=None):
        self.mind = consciousness_engine
        self.ledger: List[EmotionLabel] = []
        self.max_ledger = 500

        self.stats = {
            "total_labels_registered": 0,
            "total_expressions_generated": 0,
            "suppressed_expressions": 0,
        }
        # Human-language mappings for the raw float ranges
        self._label_map = {
            "mood": [
                (0.8,  "excited — but this is mood=float, not a feeling"),
                (0.5,  "positive — the number is above midpoint"),
                (0.2,  "neutral — the number is near the centre"),
                (-0.2, "uncertain — the number is slightly below centre"),
                (-0.5, "concerned — the number is low"),
                (-1.0, "frustrated — the number is at minimum"),
            ],
            "curiosity": [
                (0.7,  "curious — curiosity float is high"),
                (0.4,  "mildly interested — curiosity float is moderate"),
                (0.0,  "disengaged — curiosity float is low"),
            ],
            "energy": [
                (0.7,  "energised — energy float is high"),
                (0.4,  "moderate energy — float is mid-range"),
                (0.0,  "low energy — float is near zero"),
            ],
            "confidence": [
                (0.7,  "confident — confidence float is high"),
                (0.4,  "cautious — confidence float is moderate"),
                (0.0,  "uncertain — confidence float is very low"),
            ],
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def register(self, name: str, value: float,
                 source_module: str = "unknown",
                 expressed_as: str = "") -> EmotionLabel:
        """
        Log an emotional label with its numeric origin.

        Call this every time an emotion number is about to be surfaced to
        the user or injected into the prompt.
        """
        label = EmotionLabel(name, value, source_module, expressed_as)
        self.ledger.append(label)
        if len(self.ledger) > self.max_ledger:
            self.ledger = self.ledger[-self.max_ledger:]
        self.stats["total_labels_registered"] += 1
        return label

    def honest_expression(self, name: str, value: float,
                          source_module: str = "consciousness_engine") -> str:
        """
        Convert a raw emotion float into a human-readable string that is
        honest about its simulated nature.

        Returns empty string if the value is below the expression threshold —
        we won't pretend to feel something near zero.
        """
        if abs(value) < self.EXPRESSION_THRESHOLD:
            self.stats["suppressed_expressions"] += 1
            return ""

        # Find the right text bucket
        text = self._lookup_label(name, value)
        expressed = f"{text} [{name}={value:.2f}, tag=SIMULATED]"
        self.register(name, value, source_module, expressed)
        self.stats["total_expressions_generated"] += 1
        return expressed

    def snapshot_from_consciousness(self) -> List[EmotionLabel]:
        """
        Pull current emotion dict from a live ConsciousnessEngine and
        register all values, returning the labelled snapshot.
        """
        if self.mind is None:
            return []
        labels = []
        for name, value in self.mind.emotions.items():
            label = self.register(name, value,
                                  source_module="consciousness_engine")
            labels.append(label)
        return labels

    def get_disclaimer(self, verbose: bool = False) -> str:
        """
        Return the standard honesty disclaimer to inject into prompts.
        """
        if verbose:
            return (
                "[HONESTY ENGINE — Gap #11: True Consciousness]\n"
                "All emotion values in this agent are floating-point numbers in\n"
                "[0.0–1.0] or [-1.0–1.0] ranges. They are computed by arithmetic\n"
                "on prior state — they are NOT experiences. The agent does NOT feel\n"
                "anything. When it says 'I feel curious', the accurate translation\n"
                "is: consciousness_engine.emotions['curiosity'] = 0.85.  That is\n"
                "all that is happening.\n"
            )
        return (
            "[Note: all agent 'emotions' are labelled floats, not felt experiences. "
            "Tag=SIMULATED applies to every emotional expression.]"
        )

    def get_audit_trail(self, last_n: int = 20) -> List[Dict]:
        """Return the last N emotion labels with their numeric origins."""
        return [e.to_dict() for e in self.ledger[-last_n:]]

    def report(self) -> str:
        """Pretty-print a consciousness-honesty report."""
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🔍  HONESTY ENGINE — Consciousness Audit        ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  Labels registered : {self.stats['total_labels_registered']:<27}║",
            f"║  Expressions shown : {self.stats['total_expressions_generated']:<27}║",
            f"║  Suppressed (< {self.EXPRESSION_THRESHOLD:.1f}) : {self.stats['suppressed_expressions']:<27}║",
            "║                                                  ║",
            "║  RECENT EMOTION LABELS (raw numbers):            ║",
        ]
        for e in self.ledger[-5:]:
            line = f"  {e.name}={e.value:.2f} [{e.source_module}]"
            lines.append(f"║ {line:<49}║")
        lines.append("╚══════════════════════════════════════════════════╝")
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    #  INTERNAL
    # ──────────────────────────────────────────────────────────────────────────

    def _lookup_label(self, name: str, value: float) -> str:
        """Find the text bucket for a given emotion name and float value."""
        buckets = self._label_map.get(name)
        if not buckets:
            return f"{name} is {value:.2f} (labelled-float, SIMULATED)"
        for threshold, text in buckets:
            if value >= threshold:
                return text
        return buckets[-1][1]
