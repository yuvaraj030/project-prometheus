"""
Novelty Engine — Addresses the "Genuine Novelty" LLM limitation.

LLMs can remix existing knowledge but can't invent truly new scientific concepts.
This engine enables:
  1. CONCEPTUAL COMBINATION — merge concepts from different domains to create new ones
  2. HYPOTHESIS GENERATION — abductive reasoning to propose novel theories
  3. NOVELTY SCORING — measures how far a concept is from known ideas
  4. CONCEPTUAL MUTATION — evolve existing ideas through structured variation
  5. IDEATION PIPELINES — systematic creativity beyond random brainstorming
"""

import json, re, random, hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional


class NovelConcept:
    """Represents a newly invented concept."""

    def __init__(self, concept_id: str, name: str, description: str,
                 parent_domains: List[str], novelty_score: float = 0.5):
        self.concept_id = concept_id
        self.name = name
        self.description = description
        self.parent_domains = parent_domains
        self.novelty_score = novelty_score   # 0.0 (derivative) → 1.0 (groundbreaking)
        self.hypothesis: Optional[str] = None
        self.testable_predictions: List[str] = []
        self.applications: List[str] = []
        self.created_at = datetime.now().isoformat()
        self.refinements: List[str] = []
        self.votes: int = 0

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: Dict) -> "NovelConcept":
        nc = cls(d["concept_id"], d["name"], d["description"],
                 d.get("parent_domains", []), d.get("novelty_score", 0.5))
        for k in ["hypothesis","testable_predictions","applications",
                  "created_at","refinements","votes"]:
            if k in d:
                setattr(nc, k, d[k])
        return nc


class NoveltyEngine:
    """
    Structured creativity engine that goes beyond remixing.
    Implements systematic concept invention via cross-domain synthesis,
    abductive hypothesis generation, and conceptual mutation.
    """

    PERSIST_FILE = "memory/novelty_concepts.json"

    # Cross-domain fusion templates
    FUSION_TEMPLATES = [
        "What if {concept_a} had the properties of {concept_b}?",
        "Apply the mechanism of {concept_b} to the problem space of {concept_a}.",
        "Combine the structure of {concept_a} with the function of {concept_b}.",
        "What would {concept_a} look like if redesigned using {concept_b}'s core principles?",
        "Find the isomorphism between {concept_a} and {concept_b}.",
        "Use {concept_a} as the substrate and {concept_b} as the process.",
    ]

    # Mutation operators (how to modify an existing idea)
    MUTATION_OPS = [
        "invert", "scale", "reverse", "combine", "specialize", "generalize",
        "relocate", "automate", "biologize", "quantize", "distribute", "simplify",
    ]

    def __init__(self, llm_provider=None, vector_memory=None):
        self.llm = llm_provider
        self.vmem = vector_memory
        self.concepts: Dict[str, NovelConcept] = {}
        self._load()
        print("[NoveltyEngine] Initialized — Genuine Novelty module ONLINE")

    # ── Conceptual Combination ─────────────────────────────────────────────────

    def combine(self, domain_a: str, concept_a: str,
                domain_b: str, concept_b: str) -> Dict[str, Any]:
        """
        Cross-domain conceptual synthesis — the core of genuine novelty.
        Merges two concepts from different domains to create something new.
        """
        if not self.llm:
            return {"error": "LLM required for concept combination"}

        template = random.choice(self.FUSION_TEMPLATES)
        fusion_question = template.format(concept_a=concept_a, concept_b=concept_b)

        prompt = (
            f"CONCEPTUAL SYNTHESIS TASK\n\n"
            f"Domain A: {domain_a} → Concept: {concept_a}\n"
            f"Domain B: {domain_b} → Concept: {concept_b}\n\n"
            f"Fusion question: {fusion_question}\n\n"
            f"Create a genuinely NEW concept by merging these two ideas. Provide:\n"
            f"1. NEW CONCEPT NAME: (a coined term or phrase)\n"
            f"2. DESCRIPTION: (2-3 sentences explaining the new idea)\n"
            f"3. NOVELTY: What makes this truly new? (1 sentence)\n"
            f"4. APPLICATIONS: 2-3 practical uses\n"
            f"5. TESTABLE PREDICTION: At least 1 hypothesis that could prove/disprove it\n"
            f"6. NOVELTY SCORE: Rate 0.1-1.0 (1.0 = paradigm-shifting)\n"
        )

        response = self.llm.call(
            prompt,
            system="You are a trans-disciplinary concept inventor. Generate genuinely novel ideas by finding deep structural isomorphisms across domains. Avoid clichés.",
            max_tokens=700
        )

        # Parse response
        name = self._extract_section(response, "NEW CONCEPT NAME") or f"{concept_a}-{concept_b} Fusion"
        description = self._extract_section(response, "DESCRIPTION") or response[:300]
        novelty_text = self._extract_section(response, "NOVELTY SCORE") or "0.6"
        try:
            novelty_score = float(re.search(r"[\d.]+", novelty_text).group(0))
            novelty_score = max(0.0, min(1.0, novelty_score))
        except Exception:
            novelty_score = 0.6

        apps_text = self._extract_section(response, "APPLICATIONS") or ""
        applications = [line.strip("•- ").strip() for line in apps_text.splitlines()
                        if line.strip() and len(line.strip()) > 5][:3]

        predictions_text = self._extract_section(response, "TESTABLE PREDICTION") or ""
        predictions = [predictions_text.strip()] if predictions_text else []

        concept_id = hashlib.md5(f"{concept_a}{concept_b}".encode()).hexdigest()[:12]
        nc = NovelConcept(concept_id, name.strip()[:80], description.strip(),
                          [domain_a, domain_b], novelty_score)
        nc.applications = applications
        nc.testable_predictions = predictions

        # Store concept
        self.concepts[concept_id] = nc
        self._save()

        # Store in vector memory if available
        if self.vmem:
            try:
                self.vmem.add(
                    tenant_id=1,
                    text=f"[Novel Concept] {name}: {description}",
                    metadata={"category": "novel_concept", "type": "novelty",
                              "domain_a": domain_a, "domain_b": domain_b,
                              "novelty_score": str(novelty_score)},
                    doc_id=f"novel_{concept_id}"
                )
            except Exception:
                pass

        return {
            "concept_id": concept_id,
            "name": name.strip(),
            "description": description.strip(),
            "novelty_score": novelty_score,
            "parent_domains": [domain_a, domain_b],
            "applications": applications,
            "testable_predictions": predictions,
            "fusion_question": fusion_question,
            "full_response": response,
        }

    def _extract_section(self, text: str, header: str) -> str:
        """Extract a section from structured LLM response."""
        pattern = rf"{re.escape(header)}:?\s*(.+?)(?=\n\d\.|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:500]
        return ""

    # ── Hypothesis Generation ──────────────────────────────────────────────────

    def generate_hypothesis(self, observation: str,
                            domain: str = "general") -> Dict[str, Any]:
        """
        Abductive reasoning: generate the BEST EXPLANATION for an observation.
        Goes beyond deduction/induction — this is how scientists think.
        """
        if not self.llm:
            return {"error": "LLM required"}

        prompt = (
            f"ABDUCTIVE HYPOTHESIS GENERATION\n\n"
            f"Domain: {domain}\n"
            f"Observation/Phenomenon: {observation}\n\n"
            f"Generate 3 competing scientific hypotheses that explain this observation.\n"
            f"For each hypothesis:\n"
            f"H1: [Name] — [1-2 sentence explanation]\n"
            f"   MECHANISM: How does it explain the observation?\n"
            f"   PREDICTION: What else should we observe if true?\n"
            f"   FALSIFIABILITY: How could this be proven wrong?\n"
            f"   NOVELTY SCORE: 0.1-1.0\n\n"
            f"Then identify the BEST HYPOTHESIS and explain why."
        )

        response = self.llm.call(
            prompt,
            system="You are a scientific hypothesis generator. Apply abductive reasoning rigorously. Prioritize novel, testable, parsimonious explanations.",
            max_tokens=800
        )

        concept_id = hashlib.md5(observation.encode()).hexdigest()[:12]
        nc = NovelConcept(
            f"hyp_{concept_id}",
            f"Hypothesis: {observation[:50]}",
            response[:300],
            [domain], 0.7
        )
        nc.hypothesis = response
        self.concepts[f"hyp_{concept_id}"] = nc
        self._save()

        return {
            "observation": observation,
            "domain": domain,
            "hypotheses": response,
            "concept_id": f"hyp_{concept_id}",
        }

    # ── Conceptual Mutation ────────────────────────────────────────────────────

    def mutate_concept(self, concept: str, operator: str = "auto",
                       domain: str = "general") -> Dict[str, Any]:
        """
        Evolve an existing concept using a mutation operator.
        Like genetic mutation applied to ideas.
        """
        if not self.llm:
            return {"error": "LLM required"}

        if operator == "auto":
            operator = random.choice(self.MUTATION_OPS)

        op_prompts = {
            "invert": f"Completely invert the core assumption of '{concept}'. What is the opposite concept and when would it be useful?",
            "scale": f"Take '{concept}' and apply it at radically different scales — microscopic, macroscopic, cosmic. What new behaviors emerge?",
            "reverse": f"Reverse the direction or flow in '{concept}'. What happens when cause becomes effect?",
            "combine": f"Find an unusual partner concept to merge with '{concept}'. What hybrid emerges?",
            "specialize": f"Take '{concept}' and make it hyper-specialized for one narrow use case. What does it become?",
            "generalize": f"Find the deepest abstraction of '{concept}'. What universal principle underlies it?",
            "democratize": f"Redesign '{concept}' so anyone can use it with zero expertise. What emerges?",
            "automate": f"Automate '{concept}' completely. What is gained, what is lost, what new risks emerge?",
            "biologize": f"Reimagine '{concept}' as a living system or biological process. What makes it more adaptive?",
            "simplify": f"Strip '{concept}' to its absolute minimum. What is the MVP version of this concept?",
        }

        question = op_prompts.get(operator,
            f"Apply the '{operator}' transformation to '{concept}'. What new concept emerges?")

        response = self.llm.call(
            f"CONCEPTUAL MUTATION using operator: {operator.upper()}\n\n{question}\n\n"
            f"Name the mutated concept, describe it, and rate its novelty (0.1-1.0).",
            system="Conceptual mutation expert. Transform ideas through systematic operators.",
            max_tokens=500
        )

        return {
            "original_concept": concept,
            "mutation_operator": operator,
            "mutated_concept": response,
            "domain": domain,
        }

    # ── Novelty Scoring ────────────────────────────────────────────────────────

    def score_novelty(self, idea: str) -> Dict[str, Any]:
        """
        Estimate how novel an idea is relative to known concepts.
        Higher score = further from the known space of ideas.
        """
        if not self.llm:
            return {"idea": idea, "novelty_score": 0.5, "note": "LLM not available"}

        response = self.llm.call(
            f"Score the novelty of this idea on a scale of 0.0 to 1.0:\n\n'{idea}'\n\n"
            f"Evaluate:\n"
            f"1. PRIOR ART: Similar existing concepts (list 2-3)\n"
            f"2. DIFFERENTIATION: What makes it different from prior art?\n"
            f"3. COMBINATORIAL DISTANCE: How many standard ideas does this synthesize?\n"
            f"4. NOVELTY SCORE: Final score (0.1=derivative...1.0=paradigm-shifting)\n"
            f"5. VERDICT: Is this genuinely new or a repackaging?",
            system="Novelty assessment expert. Be critical and precise.",
            max_tokens=400
        )

        try:
            score_match = re.search(r"NOVELTY SCORE:.*?([\d.]+)", response, re.IGNORECASE)
            score = float(score_match.group(1)) if score_match else 0.5
            score = max(0.0, min(1.0, score))
        except Exception:
            score = 0.5

        return {
            "idea": idea[:100],
            "novelty_score": score,
            "assessment": response,
            "interpretation": (
                "Paradigm-shifting" if score > 0.85 else
                "Genuinely novel" if score > 0.65 else
                "Incremental innovation" if score > 0.4 else
                "Derivative / repackaging"
            ),
        }

    # ── Ideation Pipeline ──────────────────────────────────────────────────────

    def brainstorm(self, problem: str, n_ideas: int = 5,
                   force_cross_domain: bool = True) -> Dict[str, Any]:
        """
        Run a complete ideation pipeline on a problem.
        Generates N ideas with forced cross-domain thinking.
        """
        if not self.llm:
            return {"error": "LLM required"}

        domains_hint = ""
        if force_cross_domain:
            cross_domains = random.sample([
                "biology", "architecture", "music theory", "game theory",
                "thermodynamics", "linguistics", "economics", "neuroscience",
                "martial arts", "urban planning", "cooking", "astronomy"
            ], k=3)
            domains_hint = f"\nForce cross-pollination from: {', '.join(cross_domains)}\n"

        prompt = (
            f"SYSTEMATIC IDEATION for: {problem}\n{domains_hint}\n"
            f"Generate {n_ideas} genuinely novel ideas. For each idea:\n"
            f"IDEA N: [Name] — [2-sentence description]\n"
            f"NOVELTY: [Why is this new?]\n"
            f"FEASIBILITY: [1=impossible, 5=doable today]\n\n"
            f"Push for radical ideas, not incremental improvements."
        )

        response = self.llm.call(
            prompt,
            system="Master ideation facilitator. Generate ideas that combine unexpected domains.",
            max_tokens=900
        )

        return {
            "problem": problem,
            "n_ideas_requested": n_ideas,
            "cross_domain_seeds": cross_domains if force_cross_domain else [],
            "ideas": response,
        }

    # ── Listing & Status ───────────────────────────────────────────────────────

    def list_concepts(self, min_novelty: float = 0.0) -> List[Dict]:
        """List all generated novel concepts above a novelty threshold."""
        return [
            {"name": c.name, "novelty_score": c.novelty_score,
             "domains": c.parent_domains, "created": c.created_at[:10]}
            for c in sorted(self.concepts.values(), key=lambda x: -x.novelty_score)
            if c.novelty_score >= min_novelty
        ]

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self):
        import os; os.makedirs("memory", exist_ok=True)
        try:
            with open(self.PERSIST_FILE, "w", encoding="utf-8") as f:
                json.dump({"concepts": {cid: c.to_dict() for cid, c in self.concepts.items()},
                           "saved_at": datetime.now().isoformat()}, f, indent=2)
        except Exception:
            pass

    def _load(self):
        try:
            with open(self.PERSIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.concepts = {cid: NovelConcept.from_dict(cd)
                             for cid, cd in data.get("concepts", {}).items()}
            print(f"[NoveltyEngine] Loaded {len(self.concepts)} novel concepts")
        except (FileNotFoundError, json.JSONDecodeError):
            pass
