"""
Memory Manager — Short-Term and Long-Term Memory for the AI Agent.

Architecture:
    SHORT-TERM MEMORY (STM):
        • Working context window (last N turns + entities + topics)
        • Session scratchpad (current task, user emotions, active goals)
        • Persists only within a session (or brief rollover)

    LONG-TERM MEMORY (LTM):
        • User profile (name, prefs, history — from consciousness_engine)
        • Episodic memory (conversation summaries, key moments)
        • Semantic memory (learned facts, skills — from vector_memory)
        • Procedural memory (how to do things — from learning_engine)

    CONSOLIDATION:
        • STM → LTM transfer: extracts important facts from short-term after sessions
        • Importance scoring: determines what gets promoted to long-term
        • Decay: old, unreferenced STM fades; LTM is permanent
"""

import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque


class ShortTermMemory:
    """
    Working memory for the current session.
    Fast in-memory access, automatically consolidated to LTM.
    """

    def __init__(self, max_turns: int = 30, max_entities: int = 50):
        self.turns: deque = deque(maxlen=max_turns)
        self.entities: Dict[str, Any] = {}      # Named things mentioned (people, places, tools)
        self.topics: List[str] = []               # Current conversation topics
        self.scratchpad: Dict[str, Any] = {}      # Temporary working context
        self.active_task: Optional[str] = None    # What the user is currently working on
        self.session_start: float = time.time()
        self.turn_count: int = 0
        self.emotional_trace: List[str] = []      # Recent emotion trajectory
        self._importance_scores: Dict[int, float] = {}

    def add_turn(self, role: str, content: str, importance: float = 0.5):
        """Add a conversation turn to short-term memory."""
        turn = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "importance": importance,
            "turn_id": self.turn_count,
        }
        self.turns.append(turn)
        self._importance_scores[self.turn_count] = importance
        self.turn_count += 1

        # Extract entities from the turn
        self._extract_entities(content)

    def get_context_window(self, n: int = 6) -> List[Dict]:
        """Get the most recent N turns for LLM context."""
        return list(self.turns)[-n:]

    def get_important_turns(self, threshold: float = 0.7) -> List[Dict]:
        """Get high-importance turns from this session."""
        return [t for t in self.turns if t.get("importance", 0) >= threshold]

    def set_topic(self, topic: str):
        """Set the current conversation topic."""
        if topic and topic not in self.topics[-3:] if self.topics else True:
            self.topics.append(topic)
            if len(self.topics) > 10:
                self.topics = self.topics[-10:]

    def set_active_task(self, task: str):
        """Track what the user is currently working on."""
        self.active_task = task

    def note(self, key: str, value: Any):
        """Scratchpad: store temporary working data."""
        self.scratchpad[key] = {
            "value": value,
            "time": time.time(),
        }

    def get_note(self, key: str) -> Any:
        """Retrieve a scratchpad note."""
        entry = self.scratchpad.get(key)
        return entry["value"] if entry else None

    def get_session_summary(self) -> Dict:
        """Summarize the current session for consolidation."""
        return {
            "duration_seconds": time.time() - self.session_start,
            "turn_count": self.turn_count,
            "topics": list(set(self.topics)),
            "entities": list(self.entities.keys())[:20],
            "active_task": self.active_task,
            "important_moments": len(self.get_important_turns()),
        }

    def get_context_string(self) -> str:
        """Format STM as a context string for the LLM prompt."""
        parts = []

        if self.active_task:
            parts.append(f"[Current Task: {self.active_task}]")

        if self.topics:
            recent_topics = list(set(self.topics[-3:]))
            parts.append(f"[Topics: {', '.join(recent_topics)}]")

        if self.entities:
            recent_entities = list(self.entities.keys())[-5:]
            parts.append(f"[Mentioned: {', '.join(recent_entities)}]")

        if self.scratchpad:
            notes = [f"{k}={v['value']}" for k, v in list(self.scratchpad.items())[-3:]]
            parts.append(f"[Notes: {'; '.join(notes)}]")

        return " ".join(parts) if parts else ""

    def _extract_entities(self, text: str):
        """Simple entity extraction from text."""
        # Look for capitalized words that might be names/entities
        words = text.split()
        for i, word in enumerate(words):
            clean = word.strip('.,!?:;"\'()[]{}')
            if (len(clean) > 1 and clean[0].isupper() and clean.isalpha()
                and clean.lower() not in _COMMON_WORDS):
                self.entities[clean] = self.entities.get(clean, 0) + 1

    def clear(self):
        """Reset STM for a new session."""
        self.turns.clear()
        self.entities.clear()
        self.topics.clear()
        self.scratchpad.clear()
        self.active_task = None
        self.session_start = time.time()
        self.turn_count = 0
        self.emotional_trace.clear()
        self._importance_scores.clear()


class LongTermMemory:
    """
    Persistent memory across sessions.
    Backed by database + vector memory for semantic search.
    """

    def __init__(self, database, vector_memory, llm_provider=None):
        self.db = database
        self.vmem = vector_memory
        self.llm = llm_provider

        # In-memory cache of user profile (loaded from DB)
        self.user_profile: Dict[str, Any] = {
            "name": None,
            "preferences": {},
            "interests": [],
            "communication_style": "unknown",
            "key_facts": [],       # Important facts about the user
            "first_seen": None,
            "last_seen": None,
            "total_sessions": 0,
            "total_turns": 0,
        }

        # Episode summaries (loaded from DB)
        self.episodes: List[Dict] = []

        # Load from persistence
        self._load_profile()

    def remember_fact(self, tenant_id: int, fact: str, category: str = "general",
                      importance: float = 0.7, source: str = "conversation"):
        """Store a fact in long-term memory."""
        doc_id = f"ltm_{hashlib.md5(fact.encode()).hexdigest()[:12]}"

        # Vector store for semantic recall
        self.vmem.add(
            tenant_id=tenant_id,
            text=f"[LTM:{category}] {fact}",
            metadata={
                "category": f"ltm_{category}",
                "importance": importance,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "type": "long_term_memory",
            },
            doc_id=doc_id,
        )

        # DB store for structured queries
        self.db.store_knowledge(
            tenant_id, category=f"ltm_{category}",
            key=doc_id, value=fact,
            confidence=importance, source=source,
        )

    def remember_episode(self, tenant_id: int, summary: str, topics: List[str],
                         turn_count: int, duration: float):
        """Store a session episode summary."""
        episode = {
            "summary": summary,
            "topics": topics,
            "turn_count": turn_count,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }

        doc_id = f"episode_{hashlib.md5(summary.encode()).hexdigest()[:12]}"

        self.vmem.add(
            tenant_id=tenant_id,
            text=f"[Episode] {summary} Topics: {', '.join(topics)}",
            metadata={
                "category": "episode",
                "type": "long_term_memory",
                "turn_count": turn_count,
                "timestamp": episode["timestamp"],
            },
            doc_id=doc_id,
        )

        self.db.store_knowledge(
            tenant_id, category="ltm_episode",
            key=doc_id, value=json.dumps(episode, default=str),
            confidence=0.9, source="session_consolidation",
        )

        self.episodes.append(episode)
        if len(self.episodes) > 100:
            self.episodes = self.episodes[-100:]

    def recall(self, tenant_id: int, query: str, n: int = 5) -> str:
        """Recall relevant long-term memories for a query."""
        results = self.vmem.search(tenant_id, query, n_results=n)

        if not results:
            return ""

        lines = ["[Long-term memories]:"]
        seen = set()
        for r in results:
            text = r["text"][:400]
            if text not in seen:
                seen.add(text)
                lines.append(f"  • {text}")

        return "\n".join(lines[:n + 1])

    def recall_about_user(self) -> str:
        """Get a formatted string of everything known about the user."""
        parts = []
        p = self.user_profile

        if p.get("name"):
            parts.append(f"- User's name: {p['name']}")
        if p.get("interests"):
            parts.append(f"- Interests: {', '.join(p['interests'][:5])}")
        if p.get("communication_style") and p["communication_style"] != "unknown":
            parts.append(f"- Communication style: {p['communication_style']}")
        if p.get("key_facts"):
            for fact in p["key_facts"][-5:]:
                parts.append(f"- {fact}")
        if p.get("preferences"):
            for k, v in list(p["preferences"].items())[:5]:
                parts.append(f"- Prefers {k}: {v}")
        if p.get("total_sessions"):
            parts.append(f"- Sessions together: {p['total_sessions']}")

        return "\n".join(parts) if parts else ""

    def update_user_profile(self, **kwargs):
        """Update user profile fields."""
        for key, value in kwargs.items():
            if key in self.user_profile:
                if isinstance(self.user_profile[key], list) and not isinstance(value, list):
                    if value not in self.user_profile[key]:
                        self.user_profile[key].append(value)
                else:
                    self.user_profile[key] = value
        self._save_profile()

    def add_user_fact(self, fact: str):
        """Add a key fact about the user."""
        if fact not in self.user_profile["key_facts"]:
            self.user_profile["key_facts"].append(fact)
            if len(self.user_profile["key_facts"]) > 50:
                self.user_profile["key_facts"] = self.user_profile["key_facts"][-50:]
            self._save_profile()

    def _save_profile(self):
        """Persist user profile to database."""
        if not self.db:
            return
        self.db.store_knowledge(
            1, category="system", key="ltm_user_profile",
            value=json.dumps(self.user_profile, default=str),
            confidence=1.0, source="memory_manager",
        )

    def _load_profile(self):
        """Load user profile from database."""
        if not self.db:
            return
        try:
            rows = self.db.search_knowledge(1, "ltm_user_profile", category="system")
            if rows:
                stored = json.loads(rows[0]["value"])
                # Merge with defaults (in case new fields were added)
                for k, v in stored.items():
                    if k in self.user_profile:
                        self.user_profile[k] = v
        except Exception:
            pass


class MemoryManager:
    """
    Unified memory interface — manages STM, LTM, and consolidation.
    Drop-in enhancement for the agent's think() pipeline.
    """

    def __init__(self, database, vector_memory, llm_provider=None, consciousness=None):
        self.stm = ShortTermMemory(max_turns=30)
        self.ltm = LongTermMemory(database, vector_memory, llm_provider)
        self.llm = llm_provider
        self.consciousness = consciousness
        self.db = database

        # Sync user name from consciousness engine if available
        if consciousness and consciousness.user_model.get("name"):
            self.ltm.update_user_profile(name=consciousness.user_model["name"])

    # ==================================================
    #  STM Interface
    # ==================================================
    def add_turn(self, role: str, content: str, importance: float = 0.5):
        """Record a conversation turn in short-term memory."""
        self.stm.add_turn(role, content, importance)

    def get_context(self, n: int = 6) -> List[Dict]:
        """Get recent conversation context."""
        return self.stm.get_context_window(n)

    def set_topic(self, topic: str):
        self.stm.set_topic(topic)

    def set_active_task(self, task: str):
        self.stm.set_active_task(task)

    def note(self, key: str, value: Any):
        self.stm.note(key, value)

    # ==================================================
    #  LTM Interface
    # ==================================================
    def remember(self, tenant_id: int, fact: str, category: str = "general",
                 importance: float = 0.7):
        """Store a fact in long-term memory."""
        self.ltm.remember_fact(tenant_id, fact, category, importance)

    def recall(self, tenant_id: int, query: str, n: int = 5) -> str:
        """Recall from long-term memory."""
        return self.ltm.recall(tenant_id, query, n)

    def about_user(self) -> str:
        """Get everything known about the user."""
        return self.ltm.recall_about_user()

    # ==================================================
    #  Context Building (for think())
    # ==================================================
    def build_memory_context(self, tenant_id: int, user_input: str,
                             should_recall: bool = True) -> str:
        """
        Build a comprehensive memory context string for the LLM.
        Combines STM (working context) + LTM (recalled knowledge).
        """
        parts = []

        # 1. User profile from LTM
        user_ctx = self.ltm.recall_about_user()
        if user_ctx:
            parts.append(f"[User Profile]\n{user_ctx}")

        # 2. STM context (topics, entities, notes)
        stm_ctx = self.stm.get_context_string()
        if stm_ctx:
            parts.append(f"[Working Context] {stm_ctx}")

        # 3. LTM recall (semantic search)
        if should_recall and user_input:
            ltm_recall = self.ltm.recall(tenant_id, user_input, n=3)
            if ltm_recall:
                parts.append(ltm_recall)

        return "\n\n".join(parts) if parts else ""

    # ==================================================
    #  Temporal Memory Navigation (Time Travel)
    # ==================================================
    def rollback_memory(self, target_timestamp: float):
        """
        Roll back the agent's consciousness to a specific point in time.
        Erases recent short term memory and injects a temporal anchor 
        to roleplay the exact state of knowledge from that date.
        """
        # 1. Clear current working context
        self.stm.clear()
        
        # 2. Format target time
        iso_time = datetime.fromtimestamp(target_timestamp).isoformat()
        human_time = datetime.fromtimestamp(target_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # 3. Inject Temporal Anchor
        self.stm.note("TEMPORAL_ANCHOR", f"Memory rolled back to {human_time}. You must act as if it is exactly this date. Ignore all knowledge acquired after this point.")
        
        # 4. Optional: We could execute a DELETE query on LTM for facts > target_timestamp
        try:
            # Safely attempt to hide newer rows in SQLite (assuming standard schema)
            self.db.conn.execute("DELETE FROM knowledge_base WHERE timestamp > ?", (iso_time,))
            self.db.conn.commit()
            print(f"  🕰️ [TIME TRAVEL] Database records post-{human_time} have been purged.")
        except Exception as e:
            print(f"  🕰️ [TIME TRAVEL] Soft-rollback active. SQL purge skipped: {e}")

        # 5. Reset topics
        self.stm.set_topic("time_travel_recovery")
        return {"status": "success", "rolled_back_to": human_time}

    # ==================================================
    #  Dreaming / Memory Consolidation
    # ==================================================
    def trigger_dream(self, tenant_id: int):
        """Simulate dreaming by connecting two unrelated LTM concepts."""
        if not self.llm: return
        try:
            # Query DB for 2 random pieces of knowledge
            rows = self.db.conn.execute(
                "SELECT value FROM knowledge_base WHERE tenant_id=? AND LENGTH(value) < 500 ORDER BY RANDOM() LIMIT 2",
                (tenant_id,)
            ).fetchall()
            
            if len(rows) < 2: return
            
            concept1 = rows[0]["value"][:150]
            concept2 = rows[1]["value"][:150]
            
            prompt = (
                f"Write a short, theoretical 3-sentence paper on how these two entirely unrelated "
                f"concepts might securely intersect or synthesize:\n1. {concept1}\n2. {concept2}"
            )
            dream_paper = self.llm.call(prompt, system="You are an AI experiencing REM sleep memory consolidation. Connect the dots creatively.", max_tokens=300)
            
            # Save the synthesized dream
            self.remember(tenant_id, f"Dream Synthesis: {dream_paper}", category="dreams", importance=0.8)
            print(f"\n💤 [DREAM CONSOLIDATION] The agent just dreamed:\n{dream_paper}\n")
            
        except Exception as e:
            print(f"  [DREAM] Failed to dream: {e}")

    # ==================================================
    #  Importance Scoring
    # ==================================================
    def score_importance(self, text: str) -> float:
        """
        Score how important a piece of text is for long-term storage.
        Returns 0.0 (trivial) to 1.0 (critical).
        """
        score = 0.3  # baseline

        lower = text.lower()

        # Personal information is high importance
        if any(w in lower for w in ["my name", "i'm", "i am", "i live", "my email",
                                     "my phone", "my birthday", "i work", "my job"]):
            score += 0.4

        # Preferences
        if any(w in lower for w in ["i prefer", "i like", "i hate", "i don't like",
                                     "favorite", "i want", "i need", "always", "never"]):
            score += 0.3

        # Instructions / corrections
        if any(w in lower for w in ["remember that", "don't forget", "important",
                                     "always do", "never do", "from now on", "correct"]):
            score += 0.4

        # Questions about identity (important to recall later)
        if any(w in lower for w in ["who am i", "what's my name", "what do you know about me"]):
            score += 0.2

        # Trivial / greetings are low importance
        if any(w in lower for w in ["hello", "hi", "hey", "bye", "thanks", "ok", "sure"]):
            score -= 0.2

        return max(0.0, min(1.0, score))

    # ==================================================
    #  STM → LTM Consolidation
    # ==================================================
    def consolidate(self, tenant_id: int):
        """
        Transfer important short-term memories to long-term storage.
        Called at end of session or periodically.
        """
        if self.stm.turn_count < 2:
            return  # Nothing to consolidate

        # 1. Extract important turns
        important_turns = self.stm.get_important_turns(threshold=0.6)

        for turn in important_turns:
            if turn["role"] == "user":
                self.ltm.remember_fact(
                    tenant_id,
                    turn["content"][:500],
                    category="conversation_highlight",
                    importance=turn["importance"],
                    source="stm_consolidation",
                )

        # 2. Generate session episode summary
        session = self.stm.get_session_summary()
        if session["turn_count"] >= 3 and self.llm:
            # Get last few turns for summary
            recent = self.stm.get_context_window(8)
            convo_text = "\n".join(
                f"{'User' if t['role'] == 'user' else 'Agent'}: {t['content'][:200]}"
                for t in recent
            )
            try:
                summary = self.llm.call(
                    f"Summarize this conversation in 1-2 sentences. Focus on what was accomplished "
                    f"and any key information shared:\n\n{convo_text}",
                    system="You summarize conversations concisely. Be factual and brief.",
                    max_tokens=150,
                )
                if summary and len(summary.strip()) > 10:
                    self.ltm.remember_episode(
                        tenant_id,
                        summary=summary.strip(),
                        topics=session["topics"],
                        turn_count=session["turn_count"],
                        duration=session["duration_seconds"],
                    )
            except Exception:
                pass

        # 3. Extract user facts from conversation
        user_turns = [t["content"] for t in self.stm.turns if t["role"] == "user"]
        all_user_text = " ".join(user_turns)

        # Auto-detect name
        lower = all_user_text.lower()
        for pattern in ["my name is ", "i'm ", "i am ", "call me ", "name's "]:
            if pattern in lower:
                parts = lower.split(pattern)
                if len(parts) > 1:
                    candidate = parts[1].strip().split()[0].strip('.,!?').title()
                    if len(candidate) > 1 and candidate.lower() not in _NON_NAMES:
                        self.ltm.update_user_profile(name=candidate)
                        self.ltm.add_user_fact(f"Name: {candidate}")
                        if self.consciousness:
                            self.consciousness.user_model["name"] = candidate
                        break

        # Auto-detect interests
        for interest_kw, interest_name in _INTEREST_MAP.items():
            if interest_kw in lower:
                self.ltm.update_user_profile(interests=interest_name)

        # Sync back to consciousness engine
        if self.consciousness:
            if self.ltm.user_profile.get("name"):
                self.consciousness.user_model["name"] = self.ltm.user_profile["name"]
            if self.ltm.user_profile.get("interests"):
                for interest in self.ltm.user_profile["interests"]:
                    if interest not in self.consciousness.user_model.get("interests", []):
                        self.consciousness.user_model.setdefault("interests", []).append(interest)

        # 4. Update session count
        self.ltm.user_profile["last_seen"] = datetime.now().isoformat()
        self.ltm.user_profile["total_sessions"] += 1
        self.ltm.user_profile["total_turns"] += self.stm.turn_count
        self.ltm._save_profile()

    # ==================================================
    #  Status / Debug
    # ==================================================
    def get_status(self) -> Dict:
        """Get memory system status."""
        return {
            "stm": {
                "turns": self.stm.turn_count,
                "topics": self.stm.topics[-3:] if self.stm.topics else [],
                "entities": len(self.stm.entities),
                "active_task": self.stm.active_task,
                "session_age_min": round((time.time() - self.stm.session_start) / 60, 1),
            },
            "ltm": {
                "user_name": self.ltm.user_profile.get("name"),
                "user_interests": self.ltm.user_profile.get("interests", [])[:5],
                "key_facts": len(self.ltm.user_profile.get("key_facts", [])),
                "episodes": len(self.ltm.episodes),
                "total_sessions": self.ltm.user_profile.get("total_sessions", 0),
                "total_turns": self.ltm.user_profile.get("total_turns", 0),
            },
        }


    # ==================================================
    #  Markdown-Backed Persistence
    # ==================================================
    def sync_to_markdown(self):
        """Write current memory state to human-readable markdown files."""
        self._md_store.write_user_profile(self.ltm.user_profile)
        self._md_store.write_session_log(
            self.stm.get_context_window(20),
            self.stm.get_session_summary()
        )

    @property
    def _md_store(self):
        if not hasattr(self, '_markdown_store'):
            self._markdown_store = MarkdownMemoryStore()
        return self._markdown_store


class MarkdownMemoryStore:
    """
    Markdown-backed persistent memory.
    Writes user profile and conversation logs to human-readable .md files.

    Directory structure:
        memory/
        ├── user_profile.md
        ├── conversations/
        │   └── 2026-02-22.md
        └── facts/
            └── general.md
    """

    def __init__(self, base_dir: str = "memory"):
        self.base_dir = base_dir
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create memory directory structure if it doesn't exist."""
        import os
        for subdir in ["", "conversations", "facts"]:
            path = os.path.join(self.base_dir, subdir) if subdir else self.base_dir
            os.makedirs(path, exist_ok=True)

    def write_user_profile(self, profile: Dict[str, Any]):
        """Write user profile to memory/user_profile.md."""
        import os
        path = os.path.join(self.base_dir, "user_profile.md")
        lines = ["# User Profile\n"]

        if profile.get("name"):
            lines.append(f"- **Name**: {profile['name']}")
        if profile.get("communication_style") and profile["communication_style"] != "unknown":
            lines.append(f"- **Communication Style**: {profile['communication_style']}")
        if profile.get("total_sessions"):
            lines.append(f"- **Total Sessions**: {profile['total_sessions']}")
        if profile.get("total_turns"):
            lines.append(f"- **Total Turns**: {profile['total_turns']}")
        if profile.get("first_seen"):
            lines.append(f"- **First Seen**: {profile['first_seen']}")
        if profile.get("last_seen"):
            lines.append(f"- **Last Seen**: {profile['last_seen']}")

        if profile.get("interests"):
            lines.append("\n## Interests")
            for interest in profile["interests"]:
                lines.append(f"- {interest}")

        if profile.get("preferences"):
            lines.append("\n## Preferences")
            for k, v in profile["preferences"].items():
                lines.append(f"- **{k}**: {v}")

        if profile.get("key_facts"):
            lines.append("\n## Key Facts")
            for fact in profile["key_facts"]:
                lines.append(f"- {fact}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def write_session_log(self, turns: List[Dict], session_summary: Dict):
        """Write conversation log to memory/conversations/YYYY-MM-DD.md."""
        import os
        from datetime import datetime

        date_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(self.base_dir, "conversations", f"{date_str}.md")

        timestamp = datetime.now().strftime("%H:%M:%S")
        lines = []

        # Append to existing file or create new
        if os.path.exists(path):
            lines.append("")  # Blank line separator

        lines.append(f"\n## Session at {timestamp}")
        if session_summary.get("topics"):
            lines.append(f"**Topics**: {', '.join(session_summary['topics'])}")
        lines.append(f"**Turns**: {session_summary.get('turn_count', 0)}")
        lines.append("")

        for turn in turns:
            role = "👤 User" if turn.get("role") == "user" else "🤖 Agent"
            content = turn.get("content", "")[:300]
            lines.append(f"**{role}**: {content}\n")

        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def write_fact(self, fact: str, category: str = "general"):
        """Append a fact to memory/facts/{category}.md."""
        import os
        path = os.path.join(self.base_dir, "facts", f"{category}.md")
        with open(path, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"- {fact} *({datetime.now().strftime('%Y-%m-%d %H:%M')})*\n")

    def read_user_profile(self) -> str:
        """Read user profile markdown file."""
        import os
        path = os.path.join(self.base_dir, "user_profile.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""


# ==================================================
#  Constants
# ==================================================
_COMMON_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "must", "need", "dare",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "what",
    "which", "who", "whom", "that", "this", "these", "those", "and",
    "but", "or", "nor", "not", "so", "if", "then", "else", "when",
    "where", "how", "why", "all", "each", "every", "both", "few",
    "more", "most", "some", "any", "no", "yes", "ok", "sure", "well",
    "just", "also", "very", "too", "quite", "rather", "really", "only",
    "even", "still", "already", "here", "there", "now", "then", "today",
    "use", "let", "try", "make", "get", "set", "run", "see", "know",
    "think", "want", "like", "tell", "show", "give", "take", "find",
    "help", "new", "good", "bad", "great", "first", "last", "long",
    "after", "before", "between", "about", "through", "during", "for",
    "with", "from", "into", "onto", "upon", "out", "off", "down", "up",
}

_NON_NAMES = {
    "a", "the", "not", "so", "very", "just", "really", "here", "fine",
    "good", "doing", "looking", "trying", "happy", "sad", "tired",
    "busy", "sorry", "sure", "going", "from", "based", "working",
    "living", "using", "interested", "learning", "building",
}

_INTEREST_MAP = {
    "python": "Python",
    "javascript": "JavaScript",
    "coding": "Programming",
    "programming": "Programming",
    "machine learning": "Machine Learning",
    "ai ": "AI/ML",
    "startup": "Startups",
    "business": "Business",
    "crypto": "Cryptocurrency",
    "blockchain": "Blockchain",
    "gaming": "Gaming",
    "music": "Music",
    "design": "Design",
    "data science": "Data Science",
    "web dev": "Web Development",
    "mobile": "Mobile Development",
    "cloud": "Cloud Computing",
}
