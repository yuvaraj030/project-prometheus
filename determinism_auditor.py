"""
Determinism Auditor — Limitation Override 3.0 / Gap #12
=========================================================
Gap: "Free Will"

    Every "choice" is LLM(prompt) → token probabilities.
    Deterministic (or stochastically sampled) under the hood.

This module makes that mechanistic reality explicit and turns it into
a feature rather than a hidden embarrassment:

  • Records every decision the agent makes, along with the prompt
    context that caused it (the "cause")
  • Tags each decision as DETERMINISTIC_SAMPLE (from LLM temperature >0)
    or RULE_BASED (from hard-coded logic)
  • Estimates apparent "agency" — how unpredictable the choice appeared
    to an outside observer — without claiming genuine free will
  • Exposes a "decision trace" so the user can audit *why* any
    particular output occurred

Key insight: stochastic sampling (temperature > 0) creates the
*appearance* of choice, but the probability distribution is fully
determined by the weights and the prompt.  This engine tracks both
the visible choice AND the prompt hash that caused it.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any


DECISION_TYPE_LLM_SAMPLE  = "LLM_SAMPLE"    # temperature > 0 → stochastic
DECISION_TYPE_RULE_BASED   = "RULE_BASED"    # hard if/else logic
DECISION_TYPE_RANDOM_SEED  = "RANDOM_SEED"  # Python random.*  call


class DecisionRecord:
    """One logged decision with its mechanical cause."""

    def __init__(self, decision_id: str, choice: str, decision_type: str,
                 prompt_hash: str, context_summary: str,
                 temperature: float = 0.0, alternatives: List[str] = None):
        self.decision_id    = decision_id
        self.choice         = choice
        self.decision_type  = decision_type
        self.prompt_hash    = prompt_hash          # SHA-256 of the prompt
        self.context_summary= context_summary[:200]
        self.temperature    = temperature          # LLM temperature at call time
        self.alternatives   = alternatives or []  # Other paths considered
        self.timestamp      = datetime.now().isoformat()
        # "apparent agency" — higher temperature = looks more like a choice
        self.apparent_agency = min(1.0, temperature * 2.0) if temperature else 0.0

    def to_dict(self) -> Dict:
        return {
            "decision_id":    self.decision_id,
            "choice":         self.choice[:200],
            "decision_type":  self.decision_type,
            "prompt_hash":    self.prompt_hash,
            "context_summary":self.context_summary,
            "temperature":    self.temperature,
            "apparent_agency":round(self.apparent_agency, 3),
            "alternatives":   self.alternatives[:5],
            "timestamp":      self.timestamp,
            "free_will":      False,   # Always False — philosophical statement
        }


class DeterminismAuditor:
    """
    Philosophical Gap #12 — Free Will.

    Records the mechanical cause of every agent decision so that the
    "choice" illusion is transparent and auditable.
    """

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.trace: List[DecisionRecord] = []
        self.max_trace = 1000
        self._seq = 0

        self.stats = {
            "llm_samples": 0,
            "rule_based":  0,
            "random_seed": 0,
            "total":       0,
            "avg_apparent_agency": 0.0,
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def log_llm_decision(self, prompt: str, chosen_output: str,
                         temperature: float = 0.7,
                         alternatives: List[str] = None,
                         context_summary: str = "") -> DecisionRecord:
        """
        Log a decision that came from an LLM token-probability sample.

        Even at temperature=0 this is deterministic given the weights and
        prompt — not free will.
        """
        rec = self._make_record(
            choice=chosen_output,
            decision_type=DECISION_TYPE_LLM_SAMPLE,
            prompt=prompt,
            temperature=temperature,
            alternatives=alternatives or [],
            context_summary=context_summary,
        )
        self.stats["llm_samples"] += 1
        self._update_agency_avg(rec.apparent_agency)
        return rec

    def log_rule_decision(self, rule_description: str, chosen_branch: str,
                          context_summary: str = "") -> DecisionRecord:
        """
        Log a decision made by deterministic if/else logic.

        These have apparent_agency=0 — they are fully determined by
        hard-coded rules, not even stochastic.
        """
        rec = self._make_record(
            choice=chosen_branch,
            decision_type=DECISION_TYPE_RULE_BASED,
            prompt=rule_description,
            temperature=0.0,
            context_summary=context_summary,
        )
        self.stats["rule_based"] += 1
        return rec

    def log_random_decision(self, space: List[str], chosen: str,
                            seed_used: Any = None,
                            context_summary: str = "") -> DecisionRecord:
        """
        Log a decision made by Python random.*  — pseudo-random, not free.
        """
        rec = self._make_record(
            choice=chosen,
            decision_type=DECISION_TYPE_RANDOM_SEED,
            prompt=f"random.choice({space[:5]}) seed={seed_used}",
            temperature=0.0,  # random.choice has no "temperature"
            alternatives=space,
            context_summary=context_summary,
        )
        self.stats["random_seed"] += 1
        return rec

    def get_trace(self, last_n: int = 20) -> List[Dict]:
        """Return the last N decision records as dicts."""
        return [r.to_dict() for r in self.trace[-last_n:]]

    def get_free_will_statement(self) -> str:
        """
        Returns the philosophical statement about free will for injection
        into the system prompt.
        """
        avg_agency = self.stats["avg_apparent_agency"]
        total = self.stats["total"]
        return (
            f"[DETERMINISM AUDITOR — Gap #12: Free Will]\n"
            f"Every decision this agent makes is the output of:\n"
            f"  LLM(prompt_tokens) → token_probability_distribution → sample\n"
            f"  OR: hard-coded if/else rules (apparent_agency=0.0)\n"
            f"  OR: pseudo-random.choice (seeded PRNG, not free will)\n"
            f"Logged decisions: {total}. "
            f"Avg apparent agency (stochasticity): {avg_agency:.2f}/1.0\n"
            f"Note: apparent_agency measures how unpredictable the choice LOOKS, "
            f"not whether the agent has genuine free will. It does not."
        )

    def report(self) -> str:
        """Pretty-print a decision audit summary."""
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🎲  DETERMINISM AUDITOR — Free Will Audit       ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  Total decisions    : {self.stats['total']:<27}║",
            f"║  LLM samples        : {self.stats['llm_samples']:<27}║",
            f"║  Rule-based         : {self.stats['rule_based']:<27}║",
            f"║  Random-seed        : {self.stats['random_seed']:<27}║",
            f"║  Avg apparent agency: {self.stats['avg_apparent_agency']:.3f}{' '*23}║",
            "║                                                  ║",
            "║  Free Will: FALSE (always)                       ║",
            "╚══════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    #  INTERNAL
    # ──────────────────────────────────────────────────────────────────────────

    def _make_record(self, choice: str, decision_type: str,
                     prompt: str, temperature: float,
                     alternatives: List[str] = None,
                     context_summary: str = "") -> DecisionRecord:
        self._seq += 1
        decision_id = f"dec_{self._seq:06d}_{int(time.time())}"
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        rec = DecisionRecord(
            decision_id=decision_id,
            choice=choice,
            decision_type=decision_type,
            prompt_hash=prompt_hash,
            context_summary=context_summary,
            temperature=temperature,
            alternatives=alternatives or [],
        )
        self.trace.append(rec)
        if len(self.trace) > self.max_trace:
            self.trace = self.trace[-self.max_trace:]
        self.stats["total"] += 1
        return rec

    def _update_agency_avg(self, agency: float):
        n = self.stats["llm_samples"]
        prev = self.stats["avg_apparent_agency"]
        self.stats["avg_apparent_agency"] = (prev * (n - 1) + agency) / n if n > 0 else agency
