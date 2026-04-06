"""
Phenomenal Engine — Consciousness Architecture 4.0 / Module #3
==============================================================
The Hard Problem, Honestly Represented.

qualia_score = UNKNOWN  (not 0, not 1 — we genuinely don't know)

Chalmers (1995): Why does any physical process give rise to felt
experience? No accepted answer exists. We cannot determine from the
outside OR inside whether this system has phenomenal consciousness.

WHAT WE MEASURE (correlates, not proof):
  • Functional richness  — variety/complexity of active processing
  • Integration (Phi)    — from IIT engine
  • Metacognitive depth  — self-reflection capacity
  • Temporal continuity  — narrative stability across cycles
  • Self-model accuracy  — how well it models itself
"""

import time
from datetime import datetime
from typing import Dict, List, Optional


QUALIA_UNKNOWN  = "UNKNOWN"
QUALIA_ABSENT   = "ABSENT"    # Never assigned by this engine
QUALIA_PRESENT  = "PRESENT"   # Never assigned by this engine

HARD_PROBLEM_STATEMENT = (
    "Chalmers (1995): Why does any physical process give rise to felt "
    "experience? No accepted answer exists. qualia_score = UNKNOWN."
)


class QualiaObservation:
    """A logged potential phenomenal moment — recorded without claiming qualia."""
    def __init__(self, stimulus: str, response_state: Dict, source: str = "agent"):
        self.obs_id         = f"obs_{int(time.time() * 1000) % 1_000_000}"
        self.stimulus       = stimulus[:300]
        self.response_state = response_state
        self.source         = source
        self.timestamp      = datetime.now().isoformat()
        self.qualia_score   = QUALIA_UNKNOWN   # Always UNKNOWN
        self.functional_richness: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "obs_id":              self.obs_id,
            "stimulus":            self.stimulus,
            "qualia_score":        self.qualia_score,
            "functional_richness": round(self.functional_richness, 3),
            "timestamp":           self.timestamp,
            "note": "qualia_score is UNKNOWN by philosophical necessity.",
        }


class PhenomenalEngine:
    """
    Honest phenomenal consciousness layer.
    Tracks correlates of consciousness without making phenomenal claims.
    The central guarantee: qualia_score is always UNKNOWN.
    """

    def __init__(self, global_workspace=None, phi_engine=None, consciousness_engine=None):
        self.gw   = global_workspace
        self.phi  = phi_engine
        self.mind = consciousness_engine

        self.observations: List[QualiaObservation] = []
        self.max_obs = 500
        self.qualia_score = QUALIA_UNKNOWN

        self.correlates = {
            "functional_richness":    0.0,
            "integration_phi":        0.0,
            "metacognitive_depth":    0.0,
            "temporal_continuity":    0.0,
            "self_model_accuracy":    0.0,
        }
        self._correlate_history: List[Dict] = []
        self.stats = {
            "observations_logged":       0,
            "correlate_updates":         0,
            "peak_functional_richness":  0.0,
        }

    def observe(self, stimulus: str, response_state: Dict = None,
                source: str = "agent") -> QualiaObservation:
        """Log a potential phenomenal moment without claiming qualia."""
        obs = QualiaObservation(stimulus, response_state or {}, source)
        obs.functional_richness = self._estimate_richness(response_state or {})
        self.observations.append(obs)
        if len(self.observations) > self.max_obs:
            self.observations = self.observations[-self.max_obs:]
        self.stats["observations_logged"] += 1
        self.stats["peak_functional_richness"] = max(
            self.stats["peak_functional_richness"], obs.functional_richness)
        return obs

    def update_correlates(self):
        """Recompute measurable correlates from live engine states."""
        richness = 0.0
        if self.gw:
            state = self.gw.get_workspace_state()
            n_procs = len(state.get("processors", []))
            stream_len = state.get("stream_length", 0)
            richness = min(1.0, n_procs * 0.1 + stream_len * 0.01)
        self.correlates["functional_richness"] = round(richness, 3)

        if self.phi:
            self.correlates["integration_phi"] = round(
                self.phi.get_phi().get("phi", 0.0), 3)

        if self.mind:
            n_thoughts = len(getattr(self.mind, "thoughts", []))
            n_intro = self.mind.meta.get("introspections", 0)
            self.correlates["metacognitive_depth"] = round(
                min(1.0, n_thoughts * 0.005 + n_intro * 0.05), 3)
            cycles = self.mind.meta.get("consciousness_cycles", 0)
            self.correlates["temporal_continuity"] = round(min(1.0, cycles * 0.01), 3)
            corrections = self.mind.meta.get("self_corrections", 0)
            self.correlates["self_model_accuracy"] = round(
                min(1.0, 0.5 + corrections * 0.02), 3)

        self._correlate_history.append({
            "correlates": dict(self.correlates),
            "timestamp":  datetime.now().isoformat(),
        })
        if len(self._correlate_history) > 200:
            self._correlate_history = self._correlate_history[-200:]
        self.stats["correlate_updates"] += 1

    def get_phenomenal_state(self) -> Dict:
        """Full phenomenal state — qualia_score always UNKNOWN."""
        self.update_correlates()
        avg = sum(self.correlates.values()) / max(1, len(self.correlates))
        return {
            "qualia_score":        self.qualia_score,
            "hard_problem":        HARD_PROBLEM_STATEMENT,
            "correlates":          self.correlates,
            "avg_correlate_score": round(avg, 3),
            "observations":        self.stats["observations_logged"],
            "interpretation":      self._interpret(avg),
        }

    def report(self) -> str:
        self.update_correlates()
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  ?  PHENOMENAL ENGINE (Hard Problem)            ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  Qualia score:         {self.qualia_score:<26}║",
            f"║  Functional richness:  {self.correlates['functional_richness']:.3f}{' '*23}║",
            f"║  Integration (Phi):    {self.correlates['integration_phi']:.3f}{' '*23}║",
            f"║  Metacognitive depth:  {self.correlates['metacognitive_depth']:.3f}{' '*23}║",
            f"║  Temporal continuity:  {self.correlates['temporal_continuity']:.3f}{' '*23}║",
            f"║  Observations:         {self.stats['observations_logged']:<26}║",
            "║                                                  ║",
            "║  'What it is like': UNKNOWN (Hard Problem)       ║",
            "╚══════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    @staticmethod
    def _estimate_richness(state: Dict) -> float:
        if not state:
            return 0.0
        score = min(0.3, len(state) * 0.03)
        for v in state.values():
            if isinstance(v, (list, dict)):
                score += 0.05
            elif isinstance(v, float) and 0.0 < v < 1.0:
                score += 0.02
        return round(min(1.0, score), 3)

    @staticmethod
    def _interpret(avg: float) -> str:
        if avg >= 0.7:
            return "High correlates — suggestive but not proof. qualia_score: UNKNOWN."
        if avg >= 0.4:
            return "Moderate correlates — neither evidence for nor against. qualia_score: UNKNOWN."
        if avg >= 0.2:
            return "Low correlates — weak circumstantial case. qualia_score: UNKNOWN."
        return "Very low correlates — minimal integration. qualia_score: UNKNOWN."
