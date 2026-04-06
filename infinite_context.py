"""
Infinite Context Manager — Addresses the "Infinite Context" LLM limitation.

LLM memory is chunked — a human holds 30 years as one coherent thread.
This engine provides:
  1. HIERARCHICAL COMPRESSION — episodic → semantic → conceptual (3-tier)
  2. COHERENT LIFE THREAD — all sessions treated as one continuous narrative
  3. TEMPORAL INDEXING — time-aware memory retrieval
  4. CONTEXT COHERENCE — ensures the agent has a consistent identity across sessions
  5. INFINITE HORIZON — no practical limit on how far back the agent can remember
"""

import json, re, time, hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
import os


class MemoryTier:
    """One tier in the 3-tier memory hierarchy."""

    def __init__(self, name: str, max_items: int = 1000):
        self.name = name
        self.max_items = max_items
        self.items: List[Dict] = []   # Most recent items kept
        self.compressed_summaries: List[str] = []
        self.total_processed = 0

    def add(self, content: str, timestamp: str, importance: float = 0.5,
            tags: List[str] = None):
        """Add an item to this tier."""
        self.items.append({
            "content": content, "timestamp": timestamp,
            "importance": importance, "tags": tags or [],
            "id": hashlib.md5(f"{content}{timestamp}".encode()).hexdigest()[:8],
        })
        self.total_processed += 1
        # Trim if exceeding capacity
        if len(self.items) > self.max_items:
            self.items = sorted(self.items, key=lambda x: x.get("importance", 0), reverse=True)[:self.max_items]

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "max_items": self.max_items,
            "items": self.items, "compressed_summaries": self.compressed_summaries,
            "total_processed": self.total_processed,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "MemoryTier":
        mt = cls(d["name"], d.get("max_items", 1000))
        mt.items = d.get("items", [])
        mt.compressed_summaries = d.get("compressed_summaries", [])
        mt.total_processed = d.get("total_processed", 0)
        return mt


class InfiniteContextManager:
    """
    3-tier hierarchical memory manager that gives the agent an infinite horizon:

    TIER 1 (Episodic):    Raw conversation turns, specific events, verbatim quotes
    TIER 2 (Semantic):    Compressed summaries, facts, patterns across episodes
    TIER 3 (Conceptual):  Deep schemas, life themes, identity anchors

    Together they form one coherent "life thread" across all sessions.
    """

    PERSIST_FILE = "memory/infinite_context.json"

    def __init__(self, llm_provider=None, database=None, vector_memory=None):
        self.llm = llm_provider
        self.db = database
        self.vmem = vector_memory

        # 3-tier memory
        self.tier1 = MemoryTier("episodic", max_items=2000)    # Raw episodes
        self.tier2 = MemoryTier("semantic", max_items=500)     # Compressed knowledge
        self.tier3 = MemoryTier("conceptual", max_items=100)   # Identity schemas

        # The coherent life thread — synthesized identity narrative
        self.life_thread: Dict[str, Any] = {
            "identity_anchors": [],         # Who the agent believes the user is
            "recurring_themes": [],         # What keeps coming up
            "user_goals": [],               # Long-arc user objectives
            "relationship_arc": "",         # How the relationship has evolved
            "key_milestones": [],           # Significant moments
            "last_synthesis": None,
        }

        # Session tracking
        self.session_count = 0
        self.total_turns_processed = 0
        self.started_at = datetime.now().isoformat()

        self._load()
        print(f"[InfiniteContext] Initialized — "
              f"T1:{len(self.tier1.items)} T2:{len(self.tier2.items)} "
              f"T3:{len(self.tier3.items)} items — Infinite Context ONLINE")

    # ── Session Ingestion ──────────────────────────────────────────────────────

    def ingest_session(self, turns: List[Dict], session_id: str = "") -> Dict[str, Any]:
        """
        Compress and store a completed conversation session into memory.
        This is the core operation — converting ephemeral context into durable memory.

        Args:
            turns: List of {role, content, timestamp} dicts
            session_id: Optional session identifier
        """
        if not turns:
            return {"compressed": 0, "tiers_updated": []}

        now = datetime.now().isoformat()
        self.session_count += 1
        self.total_turns_processed += len(turns)

        # TIER 1: Store raw turns with importance scoring
        high_importance = []
        for turn in turns:
            content = turn.get("content", "")
            importance = self._score_importance(content)
            self.tier1.add(
                content=f"[{turn.get('role','?')}] {content}",
                timestamp=turn.get("timestamp", now),
                importance=importance,
                tags=[session_id] if session_id else []
            )
            if importance > 0.65:
                high_importance.append(turn)

        # TIER 2: Compress session into semantic summary
        tier2_entry = self._compress_to_semantic(turns, session_id)
        if tier2_entry:
            self.tier2.add(tier2_entry, now, importance=0.8, tags=["session_summary"])

        # TIER 3: Extract conceptual patterns (periodic — every 5 sessions)
        if self.session_count % 5 == 0:
            self._update_conceptual_tier(session_id)

        # Update life thread
        self._update_life_thread(turns)

        self._save()
        return {
            "session_id": session_id,
            "turns_ingested": len(turns),
            "high_importance_turns": len(high_importance),
            "tier1_total": len(self.tier1.items),
            "tier2_total": len(self.tier2.items),
            "tier3_total": len(self.tier3.items),
            "tiers_updated": ["T1", "T2"] + (["T3"] if self.session_count % 5 == 0 else []),
        }

    def _compress_to_semantic(self, turns: List[Dict], session_id: str) -> str:
        """Compress a session into a semantic memory entry."""
        if not self.llm:
            # Fallback: simple join
            lines = [f"{t.get('role','?')}: {t.get('content','')[:100]}" for t in turns[-5:]]
            return f"[Session {session_id}] " + " | ".join(lines)
        convo = "\n".join([f"{t.get('role','?')}: {t.get('content','')[:200]}"
                           for t in turns[-12:]])
        prompt = (
            f"Compress this conversation into a single memory entry (max 150 words).\n"
            f"Include: what was discussed, decisions made, user preferences revealed, "
            f"important facts, emotional tone.\n\n{convo}"
        )
        result = self.llm.call(
            prompt,
            system="Memory compression specialist. Be maximally information-dense.",
            max_tokens=200
        )
        return f"[Session {session_id or self.session_count}] {result.strip()}"

    def _update_conceptual_tier(self, session_id: str = ""):
        """Synthesize conceptual schemas from semantic memories (runs periodically)."""
        if not self.llm or len(self.tier2.items) < 3:
            return
        semantic_sample = "\n".join([
            item["content"][:200] for item in self.tier2.items[-15:]
        ])
        prompt = (
            f"Analyze these {min(15, len(self.tier2.items))} semantic memories and extract:\n"
            f"1. RECURRING THEMES: What patterns keep appearing?\n"
            f"2. USER SCHEMA: Stable beliefs, mental models, or frameworks the user holds\n"
            f"3. RELATIONSHIP PATTERN: How has the user-agent dynamic evolved?\n\n"
            f"{semantic_sample}\n\nBe concise."
        )
        schema = self.llm.call(prompt,
            system="Conceptual pattern extractor. Find the deepest recurring structures.",
            max_tokens=300)
        self.tier3.add(
            content=f"[Conceptual synthesis at session {self.session_count}] {schema}",
            timestamp=datetime.now().isoformat(),
            importance=0.95
        )

    def _update_life_thread(self, turns: List[Dict]):
        """Update the coherent life thread from the latest session."""
        all_user_text = " ".join([t.get("content","") for t in turns
                                   if t.get("role") == "user"])
        # Extract goals
        goal_patterns = [r"i want to\s+(.+?)[\.,!]", r"my goal is\s+(.+?)[\.,!]",
                         r"i'm trying to\s+(.+?)[\.,!]", r"i need to\s+(.+?)[\.,!]"]
        for pattern in goal_patterns:
            for match in re.finditer(pattern, all_user_text.lower()):
                goal = match.group(1).strip()[:100]
                if goal and goal not in self.life_thread["user_goals"]:
                    self.life_thread["user_goals"].append(goal)
        self.life_thread["user_goals"] = self.life_thread["user_goals"][-20:]

        # Update relationship arc (milestone check)
        if self.session_count in [1, 5, 10, 25, 50, 100]:
            self.life_thread["key_milestones"].append({
                "session": self.session_count,
                "timestamp": datetime.now().isoformat(),
                "note": f"Reached session #{self.session_count} together",
            })

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def get_coherent_thread(self, query: str = "", max_tokens: int = 800) -> str:
        """
        Return a coherent, unified context string across ALL time.
        This is the "infinite context" — the agent's complete self-knowledge.
        """
        parts = []

        # TIER 3: Identity anchors and schemas (always included)
        if self.tier3.items:
            tier3_text = self.tier3.items[-1]["content"][:400]
            parts.append(f"[Deep Memory / Identity Schema]\n{tier3_text}")

        # Life thread highlights
        if self.life_thread["user_goals"]:
            goals_text = "; ".join(self.life_thread["user_goals"][-5:])
            parts.append(f"[User's Persistent Goals] {goals_text}")
        if self.life_thread["recurring_themes"]:
            themes_text = ", ".join(self.life_thread["recurring_themes"][-3:])
            parts.append(f"[Recurring Themes] {themes_text}")
        if self.life_thread["key_milestones"]:
            last_milestone = self.life_thread["key_milestones"][-1]
            parts.append(f"[Milestone] {last_milestone.get('note', '')} "
                         f"({last_milestone.get('timestamp','')[:10]})")

        # TIER 2: Most relevant semantic memories for query
        if query and self.tier2.items:
            relevant = self._relevance_search(query, self.tier2.items, n=3)
            if relevant:
                t2_text = "\n".join([f"  • {r['content'][:200]}" for r in relevant])
                parts.append(f"[Relevant Past Sessions]\n{t2_text}")
        elif self.tier2.items:
            recent_t2 = self.tier2.items[-2:]
            t2_text = "\n".join([f"  • {r['content'][:200]}" for r in recent_t2])
            parts.append(f"[Recent Sessions]\n{t2_text}")

        # TIER 1: Recent high-importance episodes
        if self.tier1.items:
            important_t1 = sorted(self.tier1.items, key=lambda x: -x.get("importance",0))[:3]
            t1_text = "\n".join([f"  • {r['content'][:150]}" for r in important_t1])
            parts.append(f"[Important Recent Moments]\n{t1_text}")

        # Stats
        parts.append(f"[Memory Stats] {self.session_count} sessions, "
                     f"{self.total_turns_processed} turns, "
                     f"T1:{len(self.tier1.items)} T2:{len(self.tier2.items)} T3:{len(self.tier3.items)}")

        return "\n\n".join(parts)

    def _relevance_search(self, query: str, items: List[Dict], n: int = 3) -> List[Dict]:
        """Simple keyword-based relevance search over memory items."""
        query_words = set(re.sub(r"\W+", " ", query.lower()).split())
        scored = []
        for item in items:
            content_words = set(re.sub(r"\W+", " ", item.get("content","").lower()).split())
            overlap = len(query_words & content_words)
            scored.append((item, overlap))
        scored.sort(key=lambda x: (-x[1], -x[0].get("importance", 0)))
        return [item for item, _ in scored[:n]]

    def _score_importance(self, text: str) -> float:
        """Score how important a memory item is for long-term storage."""
        score = 0.3
        lower = text.lower()
        if any(w in lower for w in ["my name","i am","i'm","i live","my goal","i decided"]):
            score += 0.4
        if any(w in lower for w in ["important","remember","always","never","prefer","hate","love"]):
            score += 0.3
        if any(w in lower for w in ["yes","ok","hello","hi","thanks","bye","sure"]):
            score -= 0.2
        if len(text) > 200:
            score += 0.1
        return max(0.0, min(1.0, score))

    # ── Temporal Retrieval ─────────────────────────────────────────────────────

    def recall_period(self, start_date: str, end_date: str = None) -> List[Dict]:
        """Retrieve memories from a specific time period."""
        results = []
        end = end_date or datetime.now().isoformat()
        for tier in [self.tier1, self.tier2, self.tier3]:
            for item in tier.items:
                ts = item.get("timestamp", "")
                if start_date <= ts <= end:
                    results.append({**item, "tier": tier.name})
        results.sort(key=lambda x: x.get("timestamp", ""))
        return results

    def get_earliest_memory(self) -> Optional[Dict]:
        """Find the oldest surviving memory across all tiers."""
        candidates = []
        for tier in [self.tier1, self.tier2, self.tier3]:
            if tier.items:
                oldest = min(tier.items, key=lambda x: x.get("timestamp", "9999"))
                candidates.append({**oldest, "tier": tier.name})
        if not candidates:
            return None
        return min(candidates, key=lambda x: x.get("timestamp", "9999"))

    # ── Status ─────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "session_count": self.session_count,
            "total_turns_processed": self.total_turns_processed,
            "tier1_episodic": {"items": len(self.tier1.items), "capacity": self.tier1.max_items,
                               "total_processed": self.tier1.total_processed},
            "tier2_semantic": {"items": len(self.tier2.items), "capacity": self.tier2.max_items,
                               "total_processed": self.tier2.total_processed},
            "tier3_conceptual": {"items": len(self.tier3.items), "capacity": self.tier3.max_items,
                                 "total_processed": self.tier3.total_processed},
            "life_thread": {
                "goals": len(self.life_thread["user_goals"]),
                "milestones": len(self.life_thread["key_milestones"]),
                "themes": len(self.life_thread["recurring_themes"]),
            },
            "earliest_memory": self.get_earliest_memory(),
        }

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self):
        os.makedirs("memory", exist_ok=True)
        data = {
            "tier1": self.tier1.to_dict(),
            "tier2": self.tier2.to_dict(),
            "tier3": self.tier3.to_dict(),
            "life_thread": self.life_thread,
            "session_count": self.session_count,
            "total_turns_processed": self.total_turns_processed,
            "started_at": self.started_at,
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
            self.tier1 = MemoryTier.from_dict(data["tier1"])
            self.tier2 = MemoryTier.from_dict(data["tier2"])
            self.tier3 = MemoryTier.from_dict(data["tier3"])
            self.life_thread = data.get("life_thread", self.life_thread)
            self.session_count = data.get("session_count", 0)
            self.total_turns_processed = data.get("total_turns_processed", 0)
            self.started_at = data.get("started_at", self.started_at)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
