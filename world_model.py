"""
World Model Engine — Addresses the "World Model" LLM limitation.

LLMs have no persistent, structured model of how the physical/social world works.
Each conversation resets from zero. This engine gives the agent:
  1. PERSISTENT WORLD STATE — structured entity graph of the real world
  2. EVENT OBSERVATION — updates world state as new events occur
  3. MENTAL SIMULATION — predicts outcomes of actions before executing
  4. PHYSICS & SOCIAL RULES — persistent axioms about how the world works
  5. TIME-AWARE STATE — tracks how the world changes over time
"""

import json, re, time
from datetime import datetime
from typing import Dict, List, Any, Optional
import os


class WorldEntity:
    """Represents any entity in the world (person, place, object, concept, organization)."""

    def __init__(self, entity_id: str, name: str, entity_type: str = "object"):
        self.entity_id = entity_id
        self.name = name
        self.entity_type = entity_type      # person | place | object | org | concept | system
        self.properties: Dict[str, Any] = {}
        self.relations: List[Dict] = []     # {predicate, target_id, strength}
        self.history: List[Dict] = []       # State changes over time
        self.last_updated = datetime.now().isoformat()
        self.created_at = datetime.now().isoformat()
        self.confidence = 1.0

    def set_property(self, key: str, value: Any):
        old_value = self.properties.get(key)
        self.properties[key] = value
        if old_value != value:
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "change": f"{key}: {old_value} → {value}",
            })
        self.last_updated = datetime.now().isoformat()

    def add_relation(self, predicate: str, target_id: str, strength: float = 1.0):
        # Avoid duplicates
        for rel in self.relations:
            if rel["predicate"] == predicate and rel["target_id"] == target_id:
                rel["strength"] = strength
                return
        self.relations.append({"predicate": predicate, "target_id": target_id,
                                "strength": strength, "since": datetime.now().isoformat()})

    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id, "name": self.name, "entity_type": self.entity_type,
            "properties": self.properties, "relations": self.relations,
            "history": self.history[-20:],   # keep last 20 changes
            "last_updated": self.last_updated, "created_at": self.created_at,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "WorldEntity":
        e = cls(d["entity_id"], d["name"], d.get("entity_type", "object"))
        e.properties = d.get("properties", {})
        e.relations = d.get("relations", [])
        e.history = d.get("history", [])
        e.last_updated = d.get("last_updated", "")
        e.created_at = d.get("created_at", "")
        e.confidence = d.get("confidence", 1.0)
        return e


class WorldRule:
    """A persistent axiom about how the world works — physical, social, or logical."""

    def __init__(self, rule_id: str, description: str, category: str = "general",
                 confidence: float = 1.0, source: str = ""):
        self.rule_id = rule_id
        self.description = description
        self.category = category    # physics | social | economic | logical | biological
        self.confidence = confidence
        self.source = source
        self.validated_count = 0
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: Dict) -> "WorldRule":
        r = cls(d["rule_id"], d["description"], d.get("category","general"),
                d.get("confidence",1.0), d.get("source",""))
        r.validated_count = d.get("validated_count", 0)
        r.created_at = d.get("created_at", "")
        return r


class WorldModelEngine:
    """
    Persistent structured world model for the Ultimate AI Agent.

    Gives the agent a coherent, updateable model of the world that
    persists across all conversations — addressing the LLM world-model limitation.
    """

    PERSIST_FILE = "memory/world_model.json"

    # Default world axioms (bootstrap rules the agent knows from the start)
    DEFAULT_RULES = [
        ("physics_gravity", "Objects fall toward the Earth due to gravity", "physics", 1.0),
        ("social_trust", "Trust builds through consistent behavior over time", "social", 0.9),
        ("economic_supply", "When supply decreases and demand is constant, prices rise", "economic", 0.9),
        ("logical_causality", "Effects cannot precede their causes in time", "logical", 1.0),
        ("social_reciprocity", "Humans tend to reciprocate favors and social gestures", "social", 0.85),
        ("biology_energy", "Living systems require energy input to maintain order", "biological", 1.0),
        ("economic_incentive", "Agents act in ways that increase their perceived rewards", "economic", 0.85),
        ("physics_conservation", "Energy cannot be created or destroyed, only transformed", "physics", 1.0),
    ]

    def __init__(self, llm_provider=None, database=None):
        self.llm = llm_provider
        self.db = database
        self.entities: Dict[str, WorldEntity] = {}
        self.rules: Dict[str, WorldRule] = {}
        self.event_log: List[Dict] = []
        self._load()
        self._bootstrap_rules()
        print(f"[WorldModel] Initialized — {len(self.entities)} entities, {len(self.rules)} rules ONLINE")

    def _bootstrap_rules(self):
        """Seed default world axioms if not already present."""
        for rule_id, desc, cat, conf in self.DEFAULT_RULES:
            if rule_id not in self.rules:
                self.rules[rule_id] = WorldRule(rule_id, desc, cat, conf, "bootstrap")

    # ── Entity Management ──────────────────────────────────────────────────────

    def _entity_id(self, name: str) -> str:
        return re.sub(r"\W+", "_", name.strip().lower())[:40]

    def add_entity(self, name: str, entity_type: str = "object",
                   properties: Dict = None) -> WorldEntity:
        """Add or update an entity in the world model."""
        eid = self._entity_id(name)
        if eid not in self.entities:
            self.entities[eid] = WorldEntity(eid, name, entity_type)
        entity = self.entities[eid]
        if properties:
            for k, v in properties.items():
                entity.set_property(k, v)
        return entity

    def get_entity(self, name: str) -> Optional[WorldEntity]:
        return self.entities.get(self._entity_id(name))

    def link_entities(self, entity_a: str, predicate: str, entity_b: str,
                      strength: float = 1.0):
        """Create a relation between two entities: A --predicate--> B."""
        a = self.add_entity(entity_a)
        b = self.add_entity(entity_b)
        a.add_relation(predicate, b.entity_id, strength)
        self._save()

    # ── World State Observation ────────────────────────────────────────────────

    def observe(self, event: str, entities_mentioned: List[str] = None,
                extract_with_llm: bool = True) -> Dict[str, Any]:
        """
        Update the world model based on an observed event.
        This is how the agent "perceives" the world and updates its internal model.
        """
        event_record = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "entities": [],
            "state_changes": [],
        }

        # Auto-extract entities from text
        if extract_with_llm and self.llm:
            extracted = self._llm_extract_world_update(event)
            event_record["entities"] = extracted.get("entities", [])
            event_record["state_changes"] = extracted.get("changes", [])
            # Apply the changes
            for entity_info in extracted.get("entities", []):
                self.add_entity(
                    entity_info["name"],
                    entity_info.get("type", "object"),
                    entity_info.get("properties", {})
                )
            for rel in extracted.get("relations", []):
                self.link_entities(rel["from"], rel["predicate"], rel["to"])
        elif entities_mentioned:
            for ent_name in entities_mentioned:
                self.add_entity(ent_name)
            event_record["entities"] = entities_mentioned

        self.event_log.append(event_record)
        if len(self.event_log) > 500:   # Trim log
            self.event_log = self.event_log[-500:]
        self._save()

        return {
            "event_recorded": event[:100],
            "entities_updated": len(event_record["entities"]),
            "state_changes": len(event_record["state_changes"]),
            "total_entities": len(self.entities),
        }

    def _llm_extract_world_update(self, event: str) -> Dict[str, Any]:
        """Use LLM to extract structured world state updates from an event description."""
        prompt = (
            f"Extract world state information from this event:\n\n"
            f"EVENT: {event}\n\n"
            f"Output JSON with:\n"
            f"- entities: [{{name, type (person/place/org/object/concept), properties: {{}}}}]\n"
            f"- relations: [{{from, predicate, to}}]\n"
            f"- changes: [brief state change descriptions]\n"
            f"Keep it concise. Only include what's explicitly stated."
        )
        try:
            response = self.llm.call(prompt,
                system="World state extraction expert. Output valid JSON only.",
                max_tokens=500)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
        return {"entities": [], "relations": [], "changes": []}

    # ── Mental Simulation ──────────────────────────────────────────────────────

    def simulate(self, action: str, steps: int = 3) -> Dict[str, Any]:
        """
        Run a mental simulation of what happens if an action is taken.
        The agent 'imagines' consequences before acting — like a chess player.
        """
        if not self.llm:
            return {"error": "LLM required for simulation"}

        # Build world context
        world_ctx = self._build_world_context()
        relevant_rules = self._get_relevant_rules(action)

        prompt = (
            f"MENTAL SIMULATION\n\n"
            f"Current World State:\n{world_ctx}\n\n"
            f"Applicable World Rules:\n{relevant_rules}\n\n"
            f"Action to simulate: {action}\n\n"
            f"Simulate {steps} time steps into the future. For each step:\n"
            f"STEP N: [What changes] → [New world state]\n"
            f"FINAL OUTCOME: [Overall result and key consequences]\n"
            f"RISKS: [What could go wrong]\n"
            f"REVERSIBILITY: [Can this be undone?]"
        )

        simulation = self.llm.call(prompt,
            system="You are a world model simulator. Apply rules of cause-and-effect rigorously.",
            max_tokens=700)

        return {
            "action": action,
            "simulation_steps": steps,
            "world_state_at_simulation": f"{len(self.entities)} entities tracked",
            "simulation_result": simulation,
            "rules_applied": relevant_rules[:200],
        }

    def _build_world_context(self, max_entities: int = 10) -> str:
        """Build a concise summary of the current world state."""
        if not self.entities:
            return "World model: No entities tracked yet."
        lines = [f"World has {len(self.entities)} entities tracked."]
        # Show most recently updated entities
        sorted_ents = sorted(self.entities.values(),
                             key=lambda e: e.last_updated, reverse=True)
        for ent in sorted_ents[:max_entities]:
            props = ", ".join([f"{k}={v}" for k, v in list(ent.properties.items())[:3]])
            rels = ", ".join([f"{r['predicate']} {r['target_id']}" for r in ent.relations[:2]])
            line = f"- {ent.name} ({ent.entity_type})"
            if props:
                line += f": {props}"
            if rels:
                line += f" [{rels}]"
            lines.append(line)
        return "\n".join(lines)

    def _get_relevant_rules(self, context: str, n: int = 5) -> str:
        """Get world rules most relevant to a given context."""
        context_lower = context.lower()
        scored = []
        for rule in self.rules.values():
            score = sum(1 for word in context_lower.split()
                       if len(word) > 3 and word in rule.description.lower())
            scored.append((rule, score))
        scored.sort(key=lambda x: -x[1])
        top_rules = [r for r, s in scored[:n]]
        return "\n".join([f"- [{r.category}] {r.description}" for r in top_rules])

    # ── World Rules ────────────────────────────────────────────────────────────

    def add_rule(self, description: str, category: str = "general",
                 confidence: float = 0.9, source: str = "learned") -> Dict:
        """Add a new known rule about how the world works."""
        rid = re.sub(r"\W+", "_", description[:30].lower())
        self.rules[rid] = WorldRule(rid, description, category, confidence, source)
        self._save()
        return {"rule_id": rid, "description": description, "category": category}

    # ── Querying ───────────────────────────────────────────────────────────────

    def query_state(self, entity_name: str) -> Dict[str, Any]:
        """Get everything the agent knows about an entity."""
        entity = self.get_entity(entity_name)
        if not entity:
            return {"entity": entity_name, "known": False,
                    "total_entities": len(self.entities)}
        return {
            "entity": entity.name, "known": True, "type": entity.entity_type,
            "properties": entity.properties,
            "relations": entity.relations[:10],
            "history_length": len(entity.history),
            "last_updated": entity.last_updated,
        }

    def get_world_summary(self) -> Dict[str, Any]:
        """High-level summary of the agent's current world model."""
        type_counts: Dict[str, int] = {}
        for e in self.entities.values():
            type_counts[e.entity_type] = type_counts.get(e.entity_type, 0) + 1
        return {
            "total_entities": len(self.entities),
            "entity_types": type_counts,
            "total_rules": len(self.rules),
            "total_events_observed": len(self.event_log),
            "recent_events": [e["event"][:80] for e in self.event_log[-5:]],
            "world_context_preview": self._build_world_context(5),
        }

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self):
        os.makedirs("memory", exist_ok=True)
        data = {
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "rules": {rid: r.to_dict() for rid, r in self.rules.items()},
            "event_log": self.event_log[-200:],
            "saved_at": datetime.now().isoformat(),
        }
        try:
            with open(self.PERSIST_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        try:
            with open(self.PERSIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.entities = {eid: WorldEntity.from_dict(ed)
                             for eid, ed in data.get("entities", {}).items()}
            self.rules = {rid: WorldRule.from_dict(rd)
                          for rid, rd in data.get("rules", {}).items()}
            self.event_log = data.get("event_log", [])
            print(f"[WorldModel] Loaded {len(self.entities)} entities, "
                  f"{len(self.rules)} rules, {len(self.event_log)} events")
        except (FileNotFoundError, json.JSONDecodeError):
            pass
