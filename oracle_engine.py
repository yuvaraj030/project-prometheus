"""
The Oracle Engine (Phase 16 — The Oracle)
==========================================
Runs 10 parallel LLM simulations of a scenario with varied biases.
Clusters outcomes and returns probability-weighted predictions.
"""

import re
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


ORACLE_BIASES = [
    ("optimistic", "You are a highly optimistic analyst. Focus on best-case outcomes and opportunities."),
    ("pessimistic", "You are a cautious risk analyst. Focus on worst-case scenarios and dangers."),
    ("pragmatic", "You are a pragmatic analyst. Focus on the most likely, realistic outcomes."),
    ("contrarian", "You are a contrarian thinker. Challenge conventional wisdom and find non-obvious outcomes."),
    ("technical", "You are a technical expert. Focus on technical feasibility and implementation realities."),
    ("economic", "You are an economist. Focus on incentive structures, market forces, and financial outcomes."),
    ("historical", "You are a historian. Draw parallels with historical precedents and patterns."),
    ("systems", "You are a systems thinker. Focus on emergent properties, feedback loops, and second-order effects."),
    ("philosophical", "You are a philosopher. Examine deeper meanings, ethical implications, and definitional issues."),
    ("probabilistic", "You are a statistician. Focus on base rates, probabilities, and statistical reasoning."),
]

SYNTHESIZER_SYSTEM = (
    "You are THE ORACLE — a master predictor who has received 10 simulation results. "
    "Analyze all perspectives and produce a final probability-weighted prediction. "
    "Format your response as:\n"
    "PROBABILITY: <X>% likely\n"
    "CONFIDENCE: <low|medium|high>\n"
    "MOST LIKELY OUTCOME: <1-2 sentences>\n"
    "KEY RISKS: <1-2 sentences>\n"
    "KEY OPPORTUNITIES: <1-2 sentences>\n"
    "RECOMMENDED ACTION: <1 sentence>"
)


class OracleEngine:
    """
    The Oracle — runs 10 parallel scenario simulations and synthesizes
    probability-weighted predictions with confidence intervals.
    """

    def __init__(self, llm_provider: Any, database: Any = None):
        self.llm = llm_provider
        self.db = database
        self.oracle_history: List[Dict] = []

    async def _run_simulation(self, scenario: str, bias_name: str, bias_system: str) -> Dict:
        """Run a single simulation with a specific analytical bias."""
        sim_prompt = (
            f"Analyze this scenario and predict the outcome:\n\n{scenario}\n\n"
            "Be specific. Give a 2-3 sentence outcome prediction and a confidence %."
        )
        response = await asyncio.to_thread(
            self.llm.call, sim_prompt, system=bias_system, history=[]
        )
        return {
            "bias": bias_name,
            "prediction": response or "No prediction available.",
        }

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence percentage from text."""
        match = re.search(r'(\d{1,3})\s*%', text or "")
        if match:
            val = int(match.group(1))
            if 0 <= val <= 100:
                return val / 100.0
        return 0.5  # Default 50% if not found

    def _cluster_outcomes(self, simulations: List[Dict]) -> Dict[str, List[str]]:
        """Simple keyword-based clustering of outcomes."""
        clusters = {
            "positive": [],
            "negative": [],
            "neutral": [],
        }
        positive_words = {"likely", "will", "succeed", "growth", "benefit", "opportunity", "improve", "achieve"}
        negative_words = {"fail", "risk", "danger", "unlikely", "problem", "decline", "threat", "miss"}

        for sim in simulations:
            pred = (sim.get("prediction") or "").lower()
            pos_score = sum(1 for w in positive_words if w in pred)
            neg_score = sum(1 for w in negative_words if w in pred)
            if pos_score > neg_score:
                clusters["positive"].append(sim["bias"])
            elif neg_score > pos_score:
                clusters["negative"].append(sim["bias"])
            else:
                clusters["neutral"].append(sim["bias"])
        return clusters

    async def predict(self, scenario: str, n_simulations: int = 10, tenant_id: int = 1) -> Dict:
        """
        Run N simulations of a scenario and synthesize a probability-weighted prediction.
        """
        print(f"\n🔮 THE ORACLE — Analyzing: '{scenario[:80]}...'")
        print(f"   Running {n_simulations} parallel simulations...")
        print("=" * 60)

        # Select biases to use
        biases = ORACLE_BIASES[:n_simulations]

        # Run all simulations in parallel
        sim_tasks = [
            self._run_simulation(scenario, bias_name, bias_system)
            for bias_name, bias_system in biases
        ]
        simulations = await asyncio.gather(*sim_tasks)

        # Display simulation results
        for sim in simulations:
            print(f"  🎭 [{sim['bias'].upper()}]: {str(sim.get('prediction', ''))[:150]}")

        print("\n⚡ Oracle synthesizing final prediction...")

        # Build synthesis prompt
        sim_text = "\n\n".join([
            f"Simulation {i+1} ({s['bias']}): {s.get('prediction', '')}"
            for i, s in enumerate(simulations)
        ])
        synthesis_prompt = (
            f"SCENARIO: {scenario}\n\n"
            f"SIMULATION RESULTS:\n{sim_text}\n\n"
            "Synthesize these 10 perspectives into a final probability-weighted prediction."
        )
        final_prediction = await asyncio.to_thread(
            self.llm.call, synthesis_prompt, system=SYNTHESIZER_SYSTEM, history=[]
        )

        # Extract probability from synthesis
        probability = self._extract_confidence(final_prediction or "")
        clusters = self._cluster_outcomes(simulations)

        result = {
            "scenario": scenario,
            "n_simulations": len(simulations),
            "simulations": simulations,
            "probability": probability,
            "probability_pct": f"{probability * 100:.0f}%",
            "outcome_distribution": {
                "positive": len(clusters["positive"]),
                "negative": len(clusters["negative"]),
                "neutral": len(clusters["neutral"]),
            },
            "aligned_perspectives": clusters["positive"],
            "dissenting_perspectives": clusters["negative"],
            "final_prediction": final_prediction or "Insufficient data for prediction.",
            "timestamp": datetime.now().isoformat(),
        }

        print(f"\n🔮 ORACLE PREDICTION:")
        print(f"   {final_prediction}")
        print(f"\n   Distribution: ✅ {len(clusters['positive'])} positive | ❌ {len(clusters['negative'])} negative | ⚖️ {len(clusters['neutral'])} neutral")
        print("=" * 60)

        self.oracle_history.append(result)

        if self.db:
            try:
                self.db.audit(tenant_id, "oracle_prediction", scenario[:200])
            except Exception:
                pass

        return result

    def get_history(self, n: int = 5) -> List[Dict]:
        return self.oracle_history[-n:]

    def describe(self) -> str:
        return f"OracleEngine — {len(self.oracle_history)} predictions made. Uses 10 parallel LLM simulations."
