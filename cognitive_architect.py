"""
Cognitive Architect — Addresses the "Recursive Self-Improvement" AGI Limitation.

The agent can modify its tools but not its thinking substrate.
It's like editing habits vs. rewiring neural architecture.

This engine SIMULATES cognitive re-architecture by:
  1. BLUEPRINT MANAGEMENT  — stores modifiable cognitive schemas (system prompts,
                              reasoning chain templates, CoT structures)
  2. PERFORMANCE ANALYSIS  — monitors task success/failure signals
  3. BLUEPRINT EVOLUTION   — uses LLM to propose improved reasoning structures
  4. RUNTIME APPLICATION   — pushes updated blueprints into the running agent
  5. ARCHITECTURE HISTORY  — tracks cognitive evolution over generations

Key insight: we cannot change the LLM weights, but we CAN change:
  - The system prompt that frames every thought
  - The chain-of-thought template used for complex reasoning
  - The self-evaluation criteria used to judge responses
  - The planning schema used for goal decomposition

This is the closest possible proxy to RSI without re-training the base model.
"""

import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any


PERSIST_FILE = "memory/cognitive_blueprints.json"


# Default cognitive blueprint — the starting "cognitive architecture"
DEFAULT_BLUEPRINT = {
    "reasoning_template": (
        "THINK STEP BY STEP:\n"
        "1. Clarify: What exactly is being asked?\n"
        "2. Decompose: Break into sub-problems\n"
        "3. Recall: What do I already know about this?\n"
        "4. Infer: What can I deduce or compute?\n"
        "5. Verify: Does my answer make sense?\n"
        "6. Respond: State the conclusion clearly"
    ),
    "evaluation_criteria": [
        "Is the response factually accurate?",
        "Is the reasoning chain coherent?",
        "Is the response complete but concise?",
        "Does it directly address the user's goal?",
        "Are potential errors or limitations acknowledged?",
    ],
    "planning_schema": (
        "GOAL DECOMPOSITION:\n"
        "  1. State the end goal clearly\n"
        "  2. List prerequisite conditions\n"
        "  3. Identify sub-goals (max 5)\n"
        "  4. Assign each sub-goal an action type\n"
        "  5. Estimate confidence for each step"
    ),
    "uncertainty_protocol": (
        "When uncertain: (1) state the uncertainty, "
        "(2) give best estimate with confidence %, "
        "(3) identify what information would resolve the uncertainty"
    ),
    "generation": 1,
    "performance_score": 0.5,
    "created_at": "",
    "evolved_from": None,
}


class CognitiveBlueprint:
    """A versioned cognitive architecture specification."""

    def __init__(self, generation: int = 1, parent_id: str = None):
        import uuid
        self.blueprint_id = uuid.uuid4().hex[:12]
        self.generation = generation
        self.parent_id = parent_id

        self.reasoning_template = DEFAULT_BLUEPRINT["reasoning_template"]
        self.evaluation_criteria = list(DEFAULT_BLUEPRINT["evaluation_criteria"])
        self.planning_schema = DEFAULT_BLUEPRINT["planning_schema"]
        self.uncertainty_protocol = DEFAULT_BLUEPRINT["uncertainty_protocol"]

        # Custom additions from evolution
        self.custom_heuristics: List[str] = []
        self.domain_adaptations: Dict[str, str] = {}  # domain -> special instructions

        # Performance tracking
        self.performance_scores: List[float] = []
        self.failure_modes: List[str] = []
        self.success_patterns: List[str] = []

        self.created_at = datetime.now().isoformat()
        self.applied_count = 0

    @property
    def avg_performance(self) -> float:
        if not self.performance_scores:
            return 0.5
        return sum(self.performance_scores) / len(self.performance_scores)

    def to_dict(self) -> Dict:
        d = self.__dict__.copy()
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> "CognitiveBlueprint":
        b = object.__new__(cls)
        b.__dict__.update(d)
        return b

    def get_full_prompt_injection(self) -> str:
        """Build the complete system prompt fragment from this blueprint."""
        parts = []

        if self.reasoning_template:
            parts.append(f"REASONING FRAMEWORK:\n{self.reasoning_template}")

        if self.planning_schema:
            parts.append(f"PLANNING SCHEMA:\n{self.planning_schema}")

        if self.uncertainty_protocol:
            parts.append(f"UNCERTAINTY PROTOCOL: {self.uncertainty_protocol}")

        if self.custom_heuristics:
            h_str = "\n".join(f"  • {h}" for h in self.custom_heuristics[:5])
            parts.append(f"LEARNED HEURISTICS:\n{h_str}")

        return "\n\n".join(parts)


class CognitiveArchitect:
    """
    Runtime cognitive re-architecture engine.

    Manages, evolves, and applies cognitive blueprints — enabling the closest
    available proxy to recursive self-improvement without weight modification.
    """

    def __init__(self, llm_provider=None, database=None):
        self.llm = llm_provider
        self.db = database

        self.blueprints: Dict[str, CognitiveBlueprint] = {}
        self.active_blueprint_id: Optional[str] = None
        self.evolution_history: List[Dict] = []

        self.stats = {
            "total_evolutions": 0,
            "rewrites_applied": 0,
            "avg_performance_gain": 0.0,
            "current_generation": 1,
        }

        self._load()

        # Initialize with default blueprint if empty
        if not self.blueprints:
            self._init_default_blueprint()

    # ──────────────────────────────────────────────────────────────────────────
    #  BLUEPRINT MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────

    def _init_default_blueprint(self):
        """Create the generation-1 default blueprint."""
        b = CognitiveBlueprint(generation=1)
        self.blueprints[b.blueprint_id] = b
        self.active_blueprint_id = b.blueprint_id
        self.stats["current_generation"] = 1
        self._save()

    def get_active_blueprint(self) -> Optional[CognitiveBlueprint]:
        """Return the currently active cognitive blueprint."""
        if not self.active_blueprint_id:
            return None
        return self.blueprints.get(self.active_blueprint_id)

    def get_current_architecture(self) -> Dict:
        """Return the current cognitive architecture as a dict."""
        b = self.get_active_blueprint()
        if not b:
            return {"error": "No active blueprint"}
        return {
            "blueprint_id": b.blueprint_id,
            "generation": b.generation,
            "avg_performance": round(b.avg_performance, 3),
            "reasoning_template": b.reasoning_template,
            "planning_schema": b.planning_schema,
            "evaluation_criteria": b.evaluation_criteria,
            "uncertainty_protocol": b.uncertainty_protocol,
            "custom_heuristics": b.custom_heuristics,
            "applied_count": b.applied_count,
            "created_at": b.created_at,
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  EVOLUTION & REWRITING
    # ──────────────────────────────────────────────────────────────────────────

    def evolve_reasoning(self, performance_signal: float, context: str = "",
                          failure_description: str = "") -> Dict:
        """
        Evolve the reasoning template based on a performance signal.

        performance_signal: 0.0 (catastrophic failure) → 1.0 (perfect success)
        context:            What kind of task this was
        failure_description: If failed, what went wrong

        Returns the new blueprint if evolution occurred, or current blueprint.
        """
        current = self.get_active_blueprint()
        if not current:
            self._init_default_blueprint()
            current = self.get_active_blueprint()

        # Record performance
        current.performance_scores.append(performance_signal)
        if failure_description:
            current.failure_modes.append(failure_description[:200])
        elif performance_signal > 0.7:
            current.success_patterns.append(context[:100])

        # Only evolve if performance is consistently below threshold
        if len(current.performance_scores) < 3:
            self._save()
            return {"action": "observing", "performance": performance_signal,
                    "blueprint_id": current.blueprint_id}

        avg = current.avg_performance
        if avg >= 0.65:
            self._save()
            return {"action": "no_change", "avg_performance": avg,
                    "reason": "Performance acceptable"}

        # Performance below threshold → trigger evolution
        return self.rewrite_cognition(
            target="reasoning_template",
            reason=f"Avg performance {avg:.2f} below threshold. Failures: {failure_description[:100]}"
        )

    def rewrite_cognition(self, target: str = "all", new_spec: str = None,
                          reason: str = "") -> Dict:
        """
        Rewrite a cognitive module at runtime.

        target:   'reasoning_template' | 'planning_schema' | 'heuristics' | 'all'
        new_spec: Optional explicit specification (if None, uses LLM to generate)
        reason:   Why this rewrite is happening (for history)

        Returns the new blueprint record.
        """
        current = self.get_active_blueprint()
        if not current:
            return {"error": "No active blueprint"}

        # Create a new blueprint (child of current)
        new_gen = current.generation + 1
        new_blueprint = CognitiveBlueprint(generation=new_gen, parent_id=current.blueprint_id)

        # Inherit from parent
        new_blueprint.reasoning_template = current.reasoning_template
        new_blueprint.evaluation_criteria = list(current.evaluation_criteria)
        new_blueprint.planning_schema = current.planning_schema
        new_blueprint.uncertainty_protocol = current.uncertainty_protocol
        new_blueprint.custom_heuristics = list(current.custom_heuristics)
        new_blueprint.domain_adaptations = dict(current.domain_adaptations)

        if self.llm and new_spec is None:
            # Let LLM propose the evolution
            self._llm_evolve(new_blueprint, current, target, reason)
        elif new_spec:
            # Apply manually provided spec
            if target == "reasoning_template":
                new_blueprint.reasoning_template = new_spec
            elif target == "planning_schema":
                new_blueprint.planning_schema = new_spec
            elif target in ("heuristics", "custom_heuristics"):
                new_blueprint.custom_heuristics.append(new_spec)

        # Register and activate new blueprint
        self.blueprints[new_blueprint.blueprint_id] = new_blueprint
        old_id = self.active_blueprint_id
        self.active_blueprint_id = new_blueprint.blueprint_id

        self.stats["total_evolutions"] += 1
        self.stats["current_generation"] = new_gen

        self.evolution_history.append({
            "timestamp": datetime.now().isoformat(),
            "from_blueprint": old_id,
            "to_blueprint": new_blueprint.blueprint_id,
            "generation": new_gen,
            "reason": reason,
            "target": target,
        })

        self._save()
        return {
            "action": "evolved",
            "new_blueprint_id": new_blueprint.blueprint_id,
            "generation": new_gen,
            "target_rewritten": target,
            "reason": reason,
        }

    def _llm_evolve(self, new_blueprint: CognitiveBlueprint,
                    parent: CognitiveBlueprint, target: str, reason: str):
        """Use LLM to propose improvements to the cognitive blueprint."""
        if not self.llm:
            return

        failure_summary = "; ".join(parent.failure_modes[-3:]) if parent.failure_modes else "general improvement"
        success_summary = "; ".join(parent.success_patterns[-3:]) if parent.success_patterns else "none"

        prompt = (
            f"You are designing an improved AI reasoning framework. "
            f"The current framework has avg performance {parent.avg_performance:.2f}/1.0.\n\n"
            f"CURRENT {target.upper()}:\n{getattr(parent, target, '')}\n\n"
            f"FAILURE MODES: {failure_summary}\n"
            f"SUCCESS PATTERNS: {success_summary}\n"
            f"REASON FOR REWRITE: {reason}\n\n"
            f"Propose an IMPROVED version of the {target} that addresses these failures "
            f"and builds on successes. Be specific and actionable. "
            f"Output ONLY the improved {target} text, nothing else."
        )

        try:
            improved = self.llm.call(
                prompt,
                system="You are a cognitive architecture expert. Design better reasoning frameworks.",
                max_tokens=400
            )
            if improved and len(improved) > 30:
                if target == "reasoning_template":
                    new_blueprint.reasoning_template = improved
                elif target == "planning_schema":
                    new_blueprint.planning_schema = improved
                elif target == "all":
                    # Improve everything incrementally
                    new_blueprint.reasoning_template = improved
                    # Add a new heuristic
                    heuristic_prompt = f"Based on the failure patterns: {failure_summary}, propose ONE concise heuristic rule (max 20 words)."
                    heuristic = self.llm.call(heuristic_prompt, max_tokens=50)
                    if heuristic and len(heuristic) > 5:
                        new_blueprint.custom_heuristics.append(heuristic.strip())
        except Exception:
            pass

    def apply_blueprint(self, agent) -> bool:
        """
        Push the active blueprint into the running agent.
        Injects updated cognitive templates into the agent's system prompt base.
        """
        b = self.get_active_blueprint()
        if not b:
            return False

        try:
            injection = b.get_full_prompt_injection()
            # Store as agent attribute for inclusion in next think() call
            agent._cognitive_injection = injection
            b.applied_count += 1
            self.stats["rewrites_applied"] += 1
            self._save()
            return True
        except Exception:
            return False

    def record_performance(self, score: float, context: str = ""):
        """Record a performance score for the active blueprint."""
        b = self.get_active_blueprint()
        if b:
            b.performance_scores.append(max(0.0, min(1.0, score)))
            if context and score > 0.7:
                b.success_patterns.append(context[:100])
            self._save()

    def get_evolution_history(self, n: int = 10) -> List[Dict]:
        """Return recent evolution events."""
        return self.evolution_history[-n:]

    # ──────────────────────────────────────────────────────────────────────────
    #  PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save(self):
        os.makedirs("memory", exist_ok=True)
        try:
            with open(PERSIST_FILE, "w") as f:
                json.dump({
                    "stats": self.stats,
                    "active_blueprint_id": self.active_blueprint_id,
                    "blueprints": {k: v.to_dict() for k, v in self.blueprints.items()},
                    "evolution_history": self.evolution_history[-50:],
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
            self.active_blueprint_id = data.get("active_blueprint_id")
            self.blueprints = {
                k: CognitiveBlueprint.from_dict(v)
                for k, v in data.get("blueprints", {}).items()
            }
            self.evolution_history = data.get("evolution_history", [])
        except Exception:
            pass
