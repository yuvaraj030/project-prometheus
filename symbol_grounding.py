"""
Symbol Grounding Engine — Addresses the "True Symbol Grounding" AGI Limitation.

The Symbol Grounding Problem: for a text model, "apple" is a token cluster,
not a concept tied to color, taste, smell, weight, texture, sound when bitten.

This engine provides the best available text-based proxy:
  1. PERCEPTUAL METADATA — links tokens to richly described sensory properties
  2. MULTI-MODAL GROUNDING — uses VisionEngine when images are available
  3. AFFORDANCE MAPPING   — what can you DO with this object/concept?
  4. CROSS-MODAL SYNTHESIS — builds unified concept representations
  5. EMBODIED LOOKUP       — enriches prompts with perceptual context

This doesn't solve the Symbol Grounding Problem (unsolvable without real
perception), but it dramatically enriches the agent's concept representations
beyond pure statistical token co-occurrence.
"""

import json
import os
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any


PERSIST_FILE = "memory/symbol_percepts.json"


class Percept:
    """
    A grounded perceptual record for a concept.
    Links a text symbol to multi-modal sensory attributes.
    """

    def __init__(self, concept: str, description: str = ""):
        self.concept_id = hashlib.sha256(concept.lower().encode()).hexdigest()[:12]
        self.concept = concept.lower().strip()
        self.description = description

        # Sensory attributes (the grounding)
        self.visual: str = ""           # What does it look like?
        self.auditory: str = ""         # What does it sound like?
        self.tactile: str = ""          # What does it feel like?
        self.olfactory: str = ""        # What does it smell like?
        self.gustatory: str = ""        # What does it taste like?
        self.spatial: str = ""          # Size, shape, spatial relations
        self.temporal: str = ""         # How does it change over time?

        # Affordance and relational structure
        self.affordances: List[str] = []   # What can you do with it?
        self.is_a: List[str] = []          # Category membership
        self.has_parts: List[str] = []     # Component structure
        self.typical_contexts: List[str] = []  # Where/when encountered?
        self.related_concepts: List[str] = []  # Near neighbors

        # Metadata
        self.grounding_sources: List[str] = []   # How was this grounded?
        self.confidence: float = 0.5
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.image_described: bool = False

    def to_dict(self) -> Dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: Dict) -> "Percept":
        p = object.__new__(cls)
        p.__dict__.update(d)
        return p

    def get_grounding_summary(self) -> str:
        """Return a rich textual grounding for use in prompts."""
        parts = [f"[GROUNDED CONCEPT: {self.concept}]"]
        if self.description:
            parts.append(f"  Definition: {self.description}")
        if self.visual:
            parts.append(f"  Visual: {self.visual}")
        if self.tactile:
            parts.append(f"  Tactile: {self.tactile}")
        if self.auditory:
            parts.append(f"  Auditory: {self.auditory}")
        if self.affordances:
            parts.append(f"  Affordances: {', '.join(self.affordances[:4])}")
        if self.typical_contexts:
            parts.append(f"  Contexts: {', '.join(self.typical_contexts[:3])}")
        if self.is_a:
            parts.append(f"  Category: {', '.join(self.is_a[:3])}")
        return "\n".join(parts)


class SymbolGroundingEngine:
    """
    Multi-modal concept grounding engine.

    Associates text symbols with rich perceptual metadata, creating the
    closest available proxy to true symbol grounding in a text-based system.
    Integrates with VisionEngine for image-based grounding when available.
    """

    def __init__(self, llm_provider=None, vision_engine=None, database=None):
        self.llm = llm_provider
        self.vision = vision_engine
        self.db = database

        self.percepts: Dict[str, Percept] = {}   # concept_id -> Percept

        self.stats = {
            "total_grounded": 0,
            "vision_grounded": 0,
            "llm_grounded": 0,
            "lookups": 0,
        }

        self._load()
        self._bootstrap_core_concepts()

    # ──────────────────────────────────────────────────────────────────────────
    #  CORE API
    # ──────────────────────────────────────────────────────────────────────────

    def ground_concept(self, concept: str, description: str = "",
                       image_path: str = None,
                       sensory_attrs: Dict = None) -> Dict:
        """
        Ground a concept symbol by linking it to perceptual metadata.

        If image_path is provided → uses VisionEngine for visual grounding.
        Otherwise → uses LLM to synthesize sensory attribute descriptions.

        Args:
            concept:      The text symbol to ground (e.g., "apple", "justice")
            description:  Optional explicit definition
            image_path:   Optional path to an image for vision-based grounding
            sensory_attrs: Optional manual sensory attribute dict to inject

        Returns:
            The grounding record dict
        """
        concept_clean = concept.lower().strip()
        concept_id = hashlib.sha256(concept_clean.encode()).hexdigest()[:12]

        # Get or create percept record
        if concept_id in self.percepts:
            p = self.percepts[concept_id]
        else:
            p = Percept(concept_clean, description)
            self.percepts[concept_id] = p

        # Vision grounding (highest quality, multi-modal)
        if image_path and self.vision:
            try:
                vision_result = self.vision.describe_image(image_path)
                p.visual = vision_result.get("description", "")[:400]
                p.grounding_sources.append("vision_engine")
                p.image_described = True
                p.confidence = min(1.0, p.confidence + 0.3)
                self.stats["vision_grounded"] += 1
            except Exception:
                pass

        # Manual attribute injection
        if sensory_attrs:
            for attr in ["visual", "auditory", "tactile", "olfactory",
                        "gustatory", "spatial", "temporal"]:
                if attr in sensory_attrs:
                    setattr(p, attr, sensory_attrs[attr])
            for attr in ["affordances", "is_a", "has_parts",
                        "typical_contexts", "related_concepts"]:
                if attr in sensory_attrs:
                    existing = getattr(p, attr, [])
                    existing.extend(sensory_attrs[attr])
                    setattr(p, attr, list(set(existing)))
            p.grounding_sources.append("manual")
            p.confidence = min(1.0, p.confidence + 0.2)

        # LLM-synthesized grounding (when not already richly grounded)
        if self.llm and (not p.visual or len(p.affordances) == 0):
            self._llm_ground(p)

        p.updated_at = datetime.now().isoformat()
        if description:
            p.description = description

        self.stats["total_grounded"] += 1
        self._save()

        return {
            "concept": p.concept,
            "concept_id": p.concept_id,
            "grounding": p.get_grounding_summary(),
            "confidence": p.confidence,
            "sources": p.grounding_sources,
        }

    def _llm_ground(self, percept: Percept):
        """Use LLM to synthesize sensory/perceptual descriptions for a concept."""
        prompt = (
            f"For the concept '{percept.concept}', provide structured perceptual information.\n"
            f"Format your response EXACTLY like this:\n"
            f"VISUAL: [what it looks like — colors, shape, size]\n"
            f"TACTILE: [what it feels like — texture, temperature, weight]\n"
            f"AUDITORY: [what sounds it makes or is associated with]\n"
            f"SPATIAL: [typical size, spatial relationships]\n"
            f"AFFORDANCES: [list 3-5 things you can DO with/to it, comma-separated]\n"
            f"IS_A: [category membership, comma-separated]\n"
            f"HAS_PARTS: [component parts, comma-separated]\n"
            f"CONTEXTS: [typical situations where encountered, comma-separated]\n"
            f"RELATED: [closely related concepts, comma-separated]"
        )
        try:
            response = self.llm.call(
                prompt,
                system="You are a sensory perception expert. Be specific, concrete, and accurate.",
                max_tokens=500
            )
            if not response:
                return

            # Parse structured response
            def extract(key: str) -> str:
                m = re.search(rf"^{key}:\s*(.+)$", response, re.MULTILINE | re.IGNORECASE)
                return m.group(1).strip() if m else ""

            def extract_list(key: str) -> List[str]:
                val = extract(key)
                return [x.strip() for x in val.split(",") if x.strip()] if val else []

            if not percept.visual:
                percept.visual = extract("VISUAL")
            if not percept.tactile:
                percept.tactile = extract("TACTILE")
            if not percept.auditory:
                percept.auditory = extract("AUDITORY")
            if not percept.spatial:
                percept.spatial = extract("SPATIAL")

            new_affordances = extract_list("AFFORDANCES")
            new_isa = extract_list("IS_A")
            new_parts = extract_list("HAS_PARTS")
            new_contexts = extract_list("CONTEXTS")
            new_related = extract_list("RELATED")

            percept.affordances = list(set(percept.affordances + new_affordances))[:10]
            percept.is_a = list(set(percept.is_a + new_isa))[:10]
            percept.has_parts = list(set(percept.has_parts + new_parts))[:10]
            percept.typical_contexts = list(set(percept.typical_contexts + new_contexts))[:10]
            percept.related_concepts = list(set(percept.related_concepts + new_related))[:10]

            percept.grounding_sources.append("llm_synthesis")
            percept.confidence = min(1.0, percept.confidence + 0.25)
            self.stats["llm_grounded"] += 1
        except Exception:
            pass

    def get_percept(self, concept: str) -> Optional[Dict]:
        """Look up grounding for a concept. Returns None if not grounded yet."""
        concept_id = hashlib.sha256(concept.lower().strip().encode()).hexdigest()[:12]
        self.stats["lookups"] += 1
        if concept_id in self.percepts:
            p = self.percepts[concept_id]
            return {
                "concept": p.concept,
                "grounding": p.get_grounding_summary(),
                "confidence": p.confidence,
                "visual": p.visual,
                "tactile": p.tactile,
                "auditory": p.auditory,
                "affordances": p.affordances,
                "is_a": p.is_a,
                "contexts": p.typical_contexts,
                "related": p.related_concepts,
            }
        return None

    def enrich_with_percepts(self, text: str, max_concepts: int = 3) -> str:
        """
        Given input text, find grounded concepts in it and append their
        perceptual context. This enriches LLM prompts with grounding information.
        """
        # Find which grounded concepts appear in the text
        text_lower = text.lower()
        matched = []
        for p in self.percepts.values():
            if p.concept in text_lower and p.confidence > 0.4:
                matched.append(p)

        if not matched:
            return text

        # Sort by confidence, take top N
        matched.sort(key=lambda p: p.confidence, reverse=True)
        enrichments = []
        for p in matched[:max_concepts]:
            enrichments.append(p.get_grounding_summary())

        if enrichments:
            return text + "\n\n" + "\n".join(enrichments)
        return text

    def describe_percept(self, concept: str) -> str:
        """Return a human-readable grounding description for a concept."""
        p = self.get_percept(concept)
        if p:
            return p["grounding"]
        # Not grounded — auto-ground it first
        result = self.ground_concept(concept)
        return result.get("grounding", f"No grounding found for '{concept}'")

    def list_grounded_concepts(self, min_confidence: float = 0.0) -> List[Dict]:
        """List all grounded concepts above a confidence threshold."""
        result = []
        for p in self.percepts.values():
            if p.confidence >= min_confidence:
                result.append({
                    "concept": p.concept,
                    "confidence": round(p.confidence, 2),
                    "sources": p.grounding_sources,
                    "has_visual": bool(p.visual),
                })
        result.sort(key=lambda x: x["confidence"], reverse=True)
        return result

    def get_stats(self) -> Dict:
        """Return engine statistics."""
        return {
            **self.stats,
            "total_concepts": len(self.percepts),
            "avg_confidence": round(
                sum(p.confidence for p in self.percepts.values()) / max(1, len(self.percepts)),
                3
            )
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  BOOTSTRAP CORE CONCEPTS
    # ──────────────────────────────────────────────────────────────────────────

    def _bootstrap_core_concepts(self):
        """
        Pre-ground a handful of foundational physical concepts so the engine
        starts with some basic grounding without needing LLM calls.
        Prevents the 'apple is just a token' failure from the very first query.
        """
        if len(self.percepts) >= 5:
            return   # Already bootstrapped

        core = {
            "apple": {
                "visual": "Small to medium round fruit, usually red, green, or yellow",
                "tactile": "Smooth, waxy skin, firm and slightly yielding flesh",
                "auditory": "Crisp crunch when bitten",
                "gustatory": "Sweet, slightly tart, floral",
                "olfactory": "Fresh, sweet, faintly floral scent",
                "affordances": ["eat", "pick", "store", "cook", "throw"],
                "is_a": ["fruit", "food", "plant product"],
            },
            "fire": {
                "visual": "Flickering orange, red, and yellow flames with dark smoke",
                "tactile": "Intense radiant heat, pain at close range, burns on contact",
                "auditory": "Crackling, hissing, roaring with wind",
                "olfactory": "Acrid smoke, wood burning, chemical depending on fuel",
                "affordances": ["warm", "cook", "destroy", "light", "signal"],
                "is_a": ["combustion", "chemical reaction", "hazard"],
            },
            "water": {
                "visual": "Transparent, colorless liquid that reflects light",
                "tactile": "Wet, cool to cold, flows, no resistance",
                "auditory": "Dripping, splashing, rushing, flowing sounds",
                "gustatory": "Tasteless or slightly mineral",
                "olfactory": "No odor when clean",
                "affordances": ["drink", "swim", "clean", "cool", "conduct"],
                "is_a": ["liquid", "molecule", "resource", "compound"],
            },
        }
        for concept, attrs in core.items():
            existing_id = hashlib.sha256(concept.encode()).hexdigest()[:12]
            if existing_id not in self.percepts:
                p = Percept(concept)
                for k, v in attrs.items():
                    if hasattr(p, k):
                        setattr(p, k, v)
                p.grounding_sources = ["bootstrap"]
                p.confidence = 0.8
                self.percepts[existing_id] = p
        self._save()

    # ──────────────────────────────────────────────────────────────────────────
    #  PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save(self):
        os.makedirs("memory", exist_ok=True)
        try:
            with open(PERSIST_FILE, "w") as f:
                json.dump({
                    "stats": self.stats,
                    "percepts": {k: v.to_dict() for k, v in self.percepts.items()},
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
            self.percepts = {
                k: Percept.from_dict(v)
                for k, v in data.get("percepts", {}).items()
            }
        except Exception:
            pass
