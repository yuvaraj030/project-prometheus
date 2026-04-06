"""
Chain-of-Thought Memory (Phase 16)
====================================
Stores the agent's reasoning steps (not just answers) in vector memory.
Allows the agent to recall WHY it made past decisions.
"""

import json
import re
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional


COT_EXTRACTOR_SYSTEM = (
    "You are a reasoning extractor. Given a question and its answer, produce a structured "
    "JSON object capturing the chain of thought. Use this exact format:\n"
    "{\n"
    '  "problem": "brief restatement of the problem",\n'
    '  "steps": ["step 1", "step 2", ...],\n'
    '  "key_assumptions": ["assumption 1", ...],\n'
    '  "alternatives_considered": ["alt 1", ...],\n'
    '  "conclusion": "one-sentence summary of what was decided"\n'
    "}\n"
    "Output ONLY valid JSON, no markdown."
)


class CoTMemory:
    """
    Chain-of-Thought Memory — captures and stores structured reasoning steps
    in the agent's vector memory for future recall.
    """

    def __init__(self, vector_memory: Any, llm_provider: Any, database: Any = None):
        self.vmem = vector_memory
        self.llm = llm_provider
        self.db = database
        self._local_cache: List[Dict] = []  # in-memory fallback

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract first valid JSON object from text."""
        try:
            # Try direct parse
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        # Try regex extraction
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    async def record(
        self,
        tenant_id: int,
        question: str,
        answer: str,
        session_id: str = "default",
    ) -> Optional[Dict]:
        """
        Asynchronously extract and store chain-of-thought for a Q/A pair.
        Returns the extracted CoT dict, or None if extraction failed.
        """
        prompt = (
            f"QUESTION: {question}\n\n"
            f"ANSWER: {answer}\n\n"
            "Extract the chain of thought as JSON."
        )
        raw = await asyncio.to_thread(
            self.llm.call, prompt, system=COT_EXTRACTOR_SYSTEM, history=[]
        )
        cot = self._extract_json(raw) if raw else None
        if not cot:
            # Minimal fallback
            cot = {
                "problem": question[:200],
                "steps": [answer[:200]],
                "key_assumptions": [],
                "alternatives_considered": [],
                "conclusion": answer[:100],
            }

        cot["timestamp"] = datetime.now().isoformat()
        cot["session_id"] = session_id

        # Ensure required keys exist (guard against partial JSON from LLM)
        cot.setdefault("problem", question[:200])
        cot.setdefault("steps", [answer[:200]])
        cot.setdefault("key_assumptions", [])
        cot.setdefault("alternatives_considered", [])
        cot.setdefault("conclusion", answer[:100])

        # Store in vector memory
        cot_text = (
            f"[CoT] Problem: {cot['problem']} | "
            f"Steps: {' → '.join(cot.get('steps', [])[:3])} | "
            f"Conclusion: {cot.get('conclusion', '')}"
        )
        try:
            self.vmem.add(
                tenant_id=tenant_id,
                text=cot_text,
                metadata={
                    "category": "cot_reasoning",
                    "session": session_id,
                    "problem": cot["problem"][:100],
                },
            )
        except Exception:
            pass

        self._local_cache.append(cot)
        return cot

    def recall_why(self, tenant_id: int, query: str, n: int = 5) -> List[Dict]:
        """Search stored reasoning chains relevant to a query."""
        try:
            results = self.vmem.search(
                tenant_id=tenant_id,
                query=query,
                n_results=n,
                category="cot_reasoning",
            )
            return results
        except Exception:
            # Fallback: keyword search in cache
            q_lower = query.lower()
            matches = [
                c for c in self._local_cache
                if q_lower in c.get("problem", "").lower()
                or q_lower in " ".join(c.get("steps", [])).lower()
            ]
            return matches[:n]

    def get_recent(self, n: int = 5) -> List[Dict]:
        """Return the N most recently stored chains."""
        return self._local_cache[-n:]

    def describe(self) -> str:
        return f"CoTMemory — {len(self._local_cache)} reasoning chains stored in-session."
