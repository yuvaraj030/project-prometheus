"""
Causal Engine — Addresses the "Causal Understanding" LLM limitation.

LLMs predict tokens; they don't truly understand cause and effect.
This engine builds a persistent directed causal graph (cause → effect),
enabling the agent to:
  1. INFER ROOT CAUSES from observed effects (backward chaining)
  2. PREDICT CONSEQUENCES of actions (forward chaining)
  3. AUTO-EXTRACT causal relationships from conversations and text
  4. Run counterfactual reasoning ("what if X hadn't happened?")
"""

import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


class CausalNode:
    """A node in the causal graph — represents an event, state, or entity."""

    def __init__(self, node_id: str, description: str, node_type: str = "event"):
        self.node_id = node_id
        self.description = description
        self.node_type = node_type          # event | state | action | condition
        self.confidence = 1.0
        self.occurrences = 1
        self.first_seen = datetime.now().isoformat()
        self.last_seen = datetime.now().isoformat()
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "description": self.description,
            "node_type": self.node_type,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "CausalNode":
        node = cls(d["node_id"], d["description"], d.get("node_type", "event"))
        node.confidence = d.get("confidence", 1.0)
        node.occurrences = d.get("occurrences", 1)
        node.first_seen = d.get("first_seen", "")
        node.last_seen = d.get("last_seen", "")
        node.metadata = d.get("metadata", {})
        return node


class CausalEdge:
    """A directed causal link: cause → effect with strength and evidence."""

    def __init__(self, cause_id: str, effect_id: str, strength: float = 0.8,
                 mechanism: str = "", evidence: str = ""):
        self.cause_id = cause_id
        self.effect_id = effect_id
        self.strength = strength        # 0.0 (weak) → 1.0 (deterministic)
        self.mechanism = mechanism      # HOW the cause leads to the effect
        self.evidence = evidence        # WHY we believe this link
        self.validated = False
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "cause_id": self.cause_id,
            "effect_id": self.effect_id,
            "strength": self.strength,
            "mechanism": self.mechanism,
            "evidence": self.evidence,
            "validated": self.validated,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "CausalEdge":
        edge = cls(
            d["cause_id"], d["effect_id"],
            d.get("strength", 0.8), d.get("mechanism", ""), d.get("evidence", "")
        )
        edge.validated = d.get("validated", False)
        edge.created_at = d.get("created_at", "")
        return edge


class CausalEngine:
    """
    Persistent causal graph engine for the Ultimate AI Agent.

    Stores cause-effect relationships, enabling true causal reasoning
    beyond token prediction.
    """

    PERSIST_FILE = "memory/causal_graph.json"

    # Regex patterns to detect causal language
    CAUSAL_PATTERNS = [
        (r"(\w[\w\s]{3,40})\s+(?:causes?|led? to|results? in|produces?|triggers?|creates?)\s+(\w[\w\s]{3,40})", 0.9),
        (r"because of\s+(\w[\w\s]{3,40}),?\s+(\w[\w\s]{3,40})\s+(?:occurs?|happens?|results?)", 0.8),
        (r"(\w[\w\s]{3,40})\s+(?:due to|owing to)\s+(\w[\w\s]{3,40})", 0.75),
        (r"if\s+(\w[\w\s]{3,40}),?\s+then\s+(\w[\w\s]{3,40})", 0.7),
        (r"(\w[\w\s]{3,40})\s+therefore\s+(\w[\w\s]{3,40})", 0.8),
        (r"(\w[\w\s]{3,40})\s+enables?\s+(\w[\w\s]{3,40})", 0.65),
        (r"(\w[\w\s]{3,40})\s+prevents?\s+(\w[\w\s]{3,40})", 0.7),
    ]

    def __init__(self, llm_provider=None, database=None):
        self.llm = llm_provider
        self.db = database
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        # adjacency: cause_id → [effect_ids]
        self.forward_adj: Dict[str, List[str]] = {}
        # reverse adjacency: effect_id → [cause_ids]
        self.backward_adj: Dict[str, List[str]] = {}
        self._load()
        print("[CausalEngine] Initialized — Causal Understanding module ONLINE")

    # ══════════════════════════════════════════════════
    #  GRAPH BUILDING
    # ══════════════════════════════════════════════════

    def _node_id(self, text: str) -> str:
        """Normalize text to a stable node ID."""
        return re.sub(r"\W+", "_", text.strip().lower())[:40]

    def add_node(self, description: str, node_type: str = "event") -> CausalNode:
        """Add or update a causal node."""
        nid = self._node_id(description)
        if nid in self.nodes:
            self.nodes[nid].occurrences += 1
            self.nodes[nid].last_seen = datetime.now().isoformat()
        else:
            self.nodes[nid] = CausalNode(nid, description, node_type)
        return self.nodes[nid]

    def add_causal_link(self, cause: str, effect: str, strength: float = 0.8,
                        mechanism: str = "", evidence: str = "") -> Dict:
        """
        Assert a causal relationship: cause → effect.

        Args:
            cause: Description of the cause
            effect: Description of the effect
            strength: Causal strength 0.0–1.0
            mechanism: How/why the cause leads to the effect
            evidence: Source of this causal claim
        """
        cause_node = self.add_node(cause, "event")
        effect_node = self.add_node(effect, "event")
        cid, eid = cause_node.node_id, effect_node.node_id

        # Check for existing edge
        existing = next((e for e in self.edges if e.cause_id == cid and e.effect_id == eid), None)
        if existing:
            # Strengthen the link
            existing.strength = min(1.0, existing.strength + 0.05)
            if mechanism:
                existing.mechanism = mechanism
            self._save()
            return {"status": "reinforced", "cause": cause, "effect": effect, "strength": existing.strength}

        edge = CausalEdge(cid, eid, strength, mechanism, evidence)
        self.edges.append(edge)

        # Update adjacency
        self.forward_adj.setdefault(cid, [])
        if eid not in self.forward_adj[cid]:
            self.forward_adj[cid].append(eid)

        self.backward_adj.setdefault(eid, [])
        if cid not in self.backward_adj[eid]:
            self.backward_adj[eid].append(cid)

        self._save()
        return {"status": "added", "cause": cause, "effect": effect, "strength": strength}

    # ══════════════════════════════════════════════════
    #  FORWARD CHAINING: predict effects
    # ══════════════════════════════════════════════════

    def predict_effect(self, action: str, depth: int = 3) -> Dict[str, Any]:
        """
        Given an action/cause, predict all downstream effects up to `depth` hops.
        Returns a causal chain with probabilities.

        This is what LLMs CANNOT do natively — structured consequence prediction.
        """
        nid = self._node_id(action)
        if nid not in self.nodes:
            # Use LLM to hypothesize effects and add to graph
            return self._llm_predict_effect(action)

        chain = []
        visited = set()
        queue = [(nid, 1.0, 0)]  # (node_id, cumulative_prob, depth)

        while queue:
            current_id, prob, d = queue.pop(0)
            if current_id in visited or d > depth:
                continue
            visited.add(current_id)

            if d > 0:  # Skip the root action itself
                node = self.nodes.get(current_id)
                chain.append({
                    "effect": node.description if node else current_id,
                    "probability": round(prob, 3),
                    "depth": d,
                })

            # Follow forward edges
            for eid in self.forward_adj.get(current_id, []):
                edge = next((e for e in self.edges if e.cause_id == current_id and e.effect_id == eid), None)
                if edge:
                    new_prob = prob * edge.strength
                    if new_prob > 0.05:  # Prune low-probability paths
                        queue.append((eid, new_prob, d + 1))

        chain.sort(key=lambda x: (-x["depth"], -x["probability"]))

        return {
            "action": action,
            "predicted_effects": chain,
            "total_consequences": len(chain),
            "causal_depth": depth,
        }

    def _llm_predict_effect(self, action: str) -> Dict[str, Any]:
        """Use LLM to generate causal predictions and store them."""
        if not self.llm:
            return {"action": action, "predicted_effects": [], "note": "LLM not available"}

        prompt = (
            f"List 3-5 likely cause-and-effect consequences of this action/event:\n"
            f"ACTION: {action}\n\n"
            f"Format each line as: CAUSE > EFFECT (strength: 0.0-1.0)\n"
            f"Be specific and logical. Think like a systems thinker."
        )
        response = self.llm.call(prompt, system="You are a causal reasoning expert. Map cause-effect chains precisely.", max_tokens=500)

        # Parse and store the generated causal links
        effects = []
        for line in response.splitlines():
            match = re.search(r"(.+?)\s*>\s*(.+?)\s*\(strength:\s*([\d.]+)\)", line)
            if match:
                cause_text, effect_text, strength = match.groups()
                strength = min(1.0, max(0.0, float(strength)))
                self.add_causal_link(cause_text.strip(), effect_text.strip(),
                                     strength, evidence="llm_inference")
                effects.append({"effect": effect_text.strip(), "probability": strength, "depth": 1})

        return {
            "action": action,
            "predicted_effects": effects,
            "source": "llm_inference",
            "stored_in_graph": len(effects),
        }

    # ══════════════════════════════════════════════════
    #  BACKWARD CHAINING: infer root causes
    # ══════════════════════════════════════════════════

    def infer_cause(self, effect: str, depth: int = 3) -> Dict[str, Any]:
        """
        Given an observed effect, trace back to root causes.
        This is causal diagnosis — understanding WHY something happened.
        """
        nid = self._node_id(effect)
        if nid not in self.nodes:
            return self._llm_infer_cause(effect)

        causes = []
        visited = set()
        queue = [(nid, 1.0, 0)]

        while queue:
            current_id, prob, d = queue.pop(0)
            if current_id in visited or d > depth:
                continue
            visited.add(current_id)

            if d > 0:
                node = self.nodes.get(current_id)
                is_root = current_id not in self.backward_adj or len(self.backward_adj.get(current_id, [])) == 0
                causes.append({
                    "cause": node.description if node else current_id,
                    "probability": round(prob, 3),
                    "depth": d,
                    "is_root_cause": is_root,
                })

            # Follow backward edges
            for cid in self.backward_adj.get(current_id, []):
                edge = next((e for e in self.edges if e.cause_id == cid and e.effect_id == current_id), None)
                if edge:
                    new_prob = prob * edge.strength
                    if new_prob > 0.05:
                        queue.append((cid, new_prob, d + 1))

        causes.sort(key=lambda x: (-x.get("is_root_cause", False), -x["probability"]))

        root_causes = [c for c in causes if c.get("is_root_cause")]
        return {
            "observed_effect": effect,
            "root_causes": root_causes,
            "all_causes": causes,
            "causal_chain_length": len(causes),
        }

    def _llm_infer_cause(self, effect: str) -> Dict[str, Any]:
        """Use LLM to infer causes and populate the graph."""
        if not self.llm:
            return {"observed_effect": effect, "root_causes": [], "note": "LLM not available"}

        prompt = (
            f"Apply causal analysis. What are the most likely ROOT CAUSES of this effect?\n"
            f"OBSERVED EFFECT: {effect}\n\n"
            f"Format: CAUSE > EFFECT (strength: 0.0-1.0, is_root: true/false)\n"
            f"Trace back at least 2 levels deep. Think like a systems analyst."
        )
        response = self.llm.call(prompt, system="You are a root cause analysis expert. Trace causal chains backwards.", max_tokens=500)

        causes = []
        for line in response.splitlines():
            match = re.search(r"(.+?)\s*>\s*(.+?)\s*\(strength:\s*([\d.]+).*?is_root:\s*(true|false)", line, re.IGNORECASE)
            if match:
                cause_text, effect_text, strength, is_root = match.groups()
                strength = min(1.0, max(0.0, float(strength)))
                self.add_causal_link(cause_text.strip(), effect_text.strip(),
                                     strength, evidence="llm_backward_inference")
                causes.append({
                    "cause": cause_text.strip(),
                    "probability": strength,
                    "is_root_cause": is_root.lower() == "true",
                    "depth": 1,
                })

        return {
            "observed_effect": effect,
            "root_causes": [c for c in causes if c.get("is_root_cause")],
            "all_causes": causes,
            "source": "llm_inference",
        }

    # ══════════════════════════════════════════════════
    #  TEXT EXTRACTION: auto-learn causal links
    # ══════════════════════════════════════════════════

    def extract_from_text(self, text: str) -> List[Dict]:
        """
        Auto-extract causal relationships from natural language text.
        Returns list of discovered cause→effect pairs.
        """
        discovered = []
        text_lower = text.lower()

        for pattern, strength in self.CAUSAL_PATTERNS:
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                cause = match.group(1).strip()
                effect = match.group(2).strip()

                # Filter out noise
                if len(cause) < 4 or len(effect) < 4:
                    continue
                if cause == effect:
                    continue

                result = self.add_causal_link(cause, effect, strength=strength,
                                              evidence=f"text_extraction: {text[:80]}")
                discovered.append({"cause": cause, "effect": effect,
                                    "strength": strength, "status": result["status"]})

        return discovered

    # ══════════════════════════════════════════════════
    #  COUNTERFACTUAL REASONING
    # ══════════════════════════════════════════════════

    def counterfactual(self, cause: str, question: str = "") -> Dict[str, Any]:
        """
        "What if X hadn't happened?" — counterfactual reasoning.
        Removes the cause node and traces what effects would be absent.
        """
        nid = self._node_id(cause)
        effects = self.forward_adj.get(nid, [])

        absent_effects = []
        for eid in effects:
            node = self.nodes.get(eid)
            if node:
                # Check if this effect has OTHER causes (would still happen)
                other_causes = [c for c in self.backward_adj.get(eid, []) if c != nid]
                would_still_happen = len(other_causes) > 0
                absent_effects.append({
                    "effect": node.description,
                    "would_still_happen": would_still_happen,
                    "alternative_causes": [self.nodes[c].description for c in other_causes if c in self.nodes],
                })

        if self.llm and question:
            llm_answer = self.llm.call(
                f"Counterfactual analysis: If '{cause}' had NOT occurred, what would be different?\n"
                f"Context question: {question}\n"
                f"Use structured causal reasoning. What effects would be absent? What chain of events changes?",
                system="You are a counterfactual reasoning expert. Analyze causal chains rigorously.",
                max_tokens=400
            )
        else:
            llm_answer = ""

        return {
            "counterfactual_cause": cause,
            "absent_effects": absent_effects,
            "effects_still_occurring": [e for e in absent_effects if e["would_still_happen"]],
            "effects_prevented": [e for e in absent_effects if not e["would_still_happen"]],
            "llm_analysis": llm_answer,
        }

    # ══════════════════════════════════════════════════
    #  GRAPH STATUS & QUERYING
    # ══════════════════════════════════════════════════

    def get_graph_stats(self) -> Dict:
        """Return statistics about the causal graph."""
        root_causes = [nid for nid in self.nodes
                       if nid not in self.backward_adj or len(self.backward_adj.get(nid, [])) == 0]
        terminal_effects = [nid for nid in self.nodes
                            if nid not in self.forward_adj or len(self.forward_adj.get(nid, [])) == 0]

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "root_causes": len(root_causes),
            "terminal_effects": len(terminal_effects),
            "most_connected": self._most_connected(),
        }

    def _most_connected(self, n: int = 5) -> List[Dict]:
        """Return the N most causally connected nodes."""
        scores = {}
        for nid in self.nodes:
            out_degree = len(self.forward_adj.get(nid, []))
            in_degree = len(self.backward_adj.get(nid, []))
            scores[nid] = out_degree + in_degree

        top = sorted(scores.items(), key=lambda x: -x[1])[:n]
        return [{"node": self.nodes[nid].description, "connections": c}
                for nid, c in top if nid in self.nodes]

    def get_causal_chain(self, cause: str, effect: str) -> List[str]:
        """Find the shortest causal path between cause and effect (BFS)."""
        start = self._node_id(cause)
        end = self._node_id(effect)

        if start not in self.nodes or end not in self.nodes:
            return []

        queue = [[start]]
        visited = {start}

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if current == end:
                return [self.nodes[nid].description for nid in path if nid in self.nodes]

            for next_id in self.forward_adj.get(current, []):
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append(path + [next_id])

        return []  # No path found

    # ══════════════════════════════════════════════════
    #  PERSISTENCE
    # ══════════════════════════════════════════════════

    def _save(self):
        """Persist the causal graph to disk."""
        import os
        os.makedirs("memory", exist_ok=True)
        data = {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "forward_adj": self.forward_adj,
            "backward_adj": self.backward_adj,
            "saved_at": datetime.now().isoformat(),
        }
        try:
            with open(self.PERSIST_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        """Load the causal graph from disk."""
        try:
            with open(self.PERSIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.nodes = {nid: CausalNode.from_dict(nd) for nid, nd in data.get("nodes", {}).items()}
            self.edges = [CausalEdge.from_dict(ed) for ed in data.get("edges", [])]
            self.forward_adj = {k: list(v) for k, v in data.get("forward_adj", {}).items()}
            self.backward_adj = {k: list(v) for k, v in data.get("backward_adj", {}).items()}
            print(f"[CausalEngine] Loaded {len(self.nodes)} nodes, {len(self.edges)} causal links")
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # Fresh start
