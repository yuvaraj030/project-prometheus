"""
Curiosity Scheduler — Addresses the "Self-Directed Learning" AGI Limitation.

A human child seeks new experiences autonomously — driven by curiosity.
This agent waits to be asked. This engine changes that.

The CuriosityScheduler implements:
  1. KNOWLEDGE GAP DETECTION   — finds unresolved uncertainties in memory
  2. NOVELTY SIGNAL MONITORING — tracks what the agent hasn't explored yet
  3. UNCERTAINTY SPIKE ALERTS  — detects when confidence drops sharply
  4. AUTONOMOUS LEARNING CYCLES — fires learn() calls WITHOUT being prompted
  5. CURIOSITY STATE REPORTING  — self-aware curiosity introspection

Architecture:
  Background daemon thread runs every `interval_minutes`.
  Inspects conversation history, vector memory, and topic frequency.
  Autonomously triggers learning when gaps are detected.
"""

import json
import os
import re
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


PERSIST_FILE = "memory/curiosity_state.json"

# Markers that indicate uncertainty/knowledge gaps in conversation
UNCERTAINTY_MARKERS = [
    "i don't know", "not sure", "unclear", "uncertain", "i'm unsure",
    "i don't understand", "what is", "how does", "explain", "why does",
    "i haven't learned", "no information", "unknown", "can't find",
    "need to research", "haven't studied", "gap in knowledge",
]


class KnowledgeGap:
    """Represents a detected gap in the agent's knowledge."""

    def __init__(self, topic: str, source: str, urgency: float = 0.5):
        self.topic = topic
        self.source = source          # conversation | memory | external
        self.urgency = urgency        # 0.0 (low) → 1.0 (critical)
        self.detected_at = datetime.now().isoformat()
        self.learned = False
        self.learning_result: Optional[str] = None

    def to_dict(self) -> Dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: Dict) -> "KnowledgeGap":
        g = object.__new__(cls)
        g.__dict__.update(d)
        return g


class CuriosityScheduler:
    """
    Autonomous self-directed learning engine.

    Monitors knowledge gaps and fires learning cycles without user prompting.
    This is the closest practical proxy to intrinsic curiosity in a text-based agent.
    """

    def __init__(self, llm_provider=None, database=None,
                 interval_minutes: int = 20, max_gaps_per_cycle: int = 3):
        self.llm = llm_provider
        self.db = database
        self.interval_minutes = interval_minutes
        self.max_gaps_per_cycle = max_gaps_per_cycle

        self.curiosity_score = 0.5          # 0.0 = satiated, 1.0 = very curious
        self.gaps: List[KnowledgeGap] = []
        self.explored_topics: List[str] = []
        self.learning_log: List[Dict] = []
        self.running = False
        self._thread: Optional[threading.Thread] = None

        self.stats = {
            "total_gaps_detected": 0,
            "total_learning_cycles": 0,
            "topics_learned": 0,
            "last_cycle": None,
            "next_cycle": None,
        }

        self._load()

    # ──────────────────────────────────────────────────────────────────────────
    #  DAEMON CONTROL
    # ──────────────────────────────────────────────────────────────────────────

    def start(self, agent=None):
        """Start the background curiosity daemon thread."""
        self._agent = agent
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="CuriosityDaemon"
        )
        self._thread.start()
        print(f"[Curiosity] Scheduler online — checking every {self.interval_minutes} min")

    def stop(self):
        """Stop the daemon."""
        self.running = False

    def _daemon_loop(self):
        """Background loop — runs autonomously."""
        while self.running:
            try:
                self._run_cycle()
            except Exception as e:
                pass  # Never crash the daemon
            # Wait for next interval
            next_wake = datetime.now() + timedelta(minutes=self.interval_minutes)
            self.stats["next_cycle"] = next_wake.isoformat()
            self._save()
            # Sleep in short chunks to allow clean shutdown
            for _ in range(self.interval_minutes * 60 // 5):
                if not self.running:
                    break
                time.sleep(5)

    # ──────────────────────────────────────────────────────────────────────────
    #  CORE CYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def _run_cycle(self):
        """One full curiosity scan + learning cycle."""
        self.stats["last_cycle"] = datetime.now().isoformat()
        self.stats["total_learning_cycles"] += 1

        # Step 1: Detect knowledge gaps
        new_gaps = self._detect_gaps()
        self.stats["total_gaps_detected"] += len(new_gaps)

        # Step 2: Prioritize by urgency
        pending = [g for g in self.gaps if not g.learned]
        pending.sort(key=lambda g: g.urgency, reverse=True)
        to_learn = pending[:self.max_gaps_per_cycle]

        # Step 3: Autonomously trigger learning
        for gap in to_learn:
            self._learn_gap(gap)

        # Step 4: Update curiosity score
        self._update_curiosity_score()
        self._save()

    def _detect_gaps(self) -> List[KnowledgeGap]:
        """
        Scan available signals for knowledge gaps.
        Returns newly discovered gaps.
        """
        new_gaps = []

        # Signal 1: Check conversation history for uncertainty markers
        if hasattr(self, "_agent") and self._agent:
            try:
                history = list(getattr(self._agent, "conversation_history", []))[-20:]
                for msg in history:
                    text = msg.get("content", "").lower() if isinstance(msg, dict) else str(msg).lower()
                    for marker in UNCERTAINTY_MARKERS:
                        if marker in text:
                            # Extract the topic around this uncertainty
                            topic = self._extract_topic_from_uncertainty(text, marker)
                            if topic and topic not in self.explored_topics:
                                gap = KnowledgeGap(
                                    topic=topic,
                                    source="conversation",
                                    urgency=0.7
                                )
                                new_gaps.append(gap)
                                self.gaps.append(gap)
                                self.stats["total_gaps_detected"] += 1
                            break
            except Exception:
                pass

        # Signal 2: Check for topics that appear frequently but are unlearned
        if hasattr(self, "_agent") and self._agent:
            try:
                freq_topics = self._analyze_topic_frequency()
                for topic, freq in freq_topics.items():
                    if freq >= 3 and topic not in self.explored_topics:
                        gap = KnowledgeGap(
                            topic=topic,
                            source="frequency_analysis",
                            urgency=min(freq / 10.0, 0.9)
                        )
                        # Deduplicate
                        existing = [g.topic for g in self.gaps]
                        if topic not in existing:
                            new_gaps.append(gap)
                            self.gaps.append(gap)
            except Exception:
                pass

        return new_gaps

    def _extract_topic_from_uncertainty(self, text: str, marker: str) -> Optional[str]:
        """Extract the subject of uncertainty from a text snippet."""
        # Find text after the marker
        idx = text.find(marker)
        if idx == -1:
            return None
        snippet = text[idx + len(marker):idx + len(marker) + 60].strip()
        # Take first few words as the topic
        words = [w for w in snippet.split()[:5] if len(w) > 2]
        if words:
            return " ".join(words[:3])
        return None

    def _analyze_topic_frequency(self) -> Dict[str, int]:
        """Count topic frequency in recent conversation."""
        freq = {}
        if not (hasattr(self, "_agent") and self._agent):
            return freq
        history = list(getattr(self._agent, "conversation_history", []))[-30:]
        for msg in history:
            text = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            # Simple noun extraction: words > 4 chars, not common stop words
            STOP_WORDS = {"that", "this", "with", "from", "have", "will",
                         "about", "what", "when", "where", "which", "would",
                         "your", "more", "some", "they", "them", "there"}
            words = re.findall(r'\b[a-zA-Z]{5,}\b', text.lower())
            for w in words:
                if w not in STOP_WORDS:
                    freq[w] = freq.get(w, 0) + 1
        # Return only topics appearing ≥3 times
        return {k: v for k, v in freq.items() if v >= 3}

    def _learn_gap(self, gap: KnowledgeGap):
        """Autonomously trigger a learning cycle for a detected gap."""
        if not (hasattr(self, "_agent") and self._agent):
            gap.learned = True
            gap.learning_result = "No agent available"
            return

        agent = self._agent
        try:
            topic = gap.topic
            # Ask the LLM to generate a self-contained explanation
            if self.llm:
                prompt = (
                    f"Provide a concise, factual explanation of: '{topic}'. "
                    f"Focus on key concepts, definitions, and important relationships. "
                    f"Keep it under 200 words."
                )
                explanation = self.llm.call(prompt, system="You are a knowledge synthesizer. Be accurate and concise.")
                if explanation and len(explanation) > 20:
                    # Store in vector memory
                    vmem = getattr(agent, "vmem", None)
                    if vmem:
                        vmem.store(
                            tenant_id=getattr(agent, "default_tid", 1),
                            text=f"[CURIOSITY LEARNED] {topic}: {explanation}",
                            metadata={"source": "curiosity_scheduler", "topic": topic}
                        )
                    gap.learned = True
                    gap.learning_result = explanation[:300]
                    self.explored_topics.append(topic)
                    self.stats["topics_learned"] += 1
                    self.learning_log.append({
                        "topic": topic,
                        "source": gap.source,
                        "timestamp": datetime.now().isoformat(),
                        "snippet": explanation[:150],
                    })
        except Exception as e:
            gap.learning_result = f"Error: {e}"

    def _update_curiosity_score(self):
        """Recompute the agent's current curiosity level."""
        pending_gaps = len([g for g in self.gaps if not g.learned])
        # More pending gaps = higher curiosity
        self.curiosity_score = min(1.0, 0.2 + (pending_gaps / max(1, len(self.gaps) + 5)))

    # ──────────────────────────────────────────────────────────────────────────
    #  MANUAL API
    # ──────────────────────────────────────────────────────────────────────────

    def trigger_learning_cycle(self, topic: str = None) -> Dict:
        """
        Manually trigger a learning cycle (for /curiosity learn <topic> command).
        If topic is provided, learns that exact topic.
        Otherwise runs a full gap scan cycle.
        """
        if topic:
            gap = KnowledgeGap(topic=topic, source="manual", urgency=0.9)
            self.gaps.append(gap)
            self._learn_gap(gap)
            self._save()
            return {
                "topic": topic,
                "learned": gap.learned,
                "result": gap.learning_result,
            }
        else:
            gaps_before = len([g for g in self.gaps if not g.learned])
            self._run_cycle()
            gaps_after = len([g for g in self.gaps if not g.learned])
            return {
                "gaps_found": len(self.gaps),
                "gaps_resolved": gaps_before - gaps_after,
                "curiosity_score": self.curiosity_score,
            }

    def add_gap(self, topic: str, urgency: float = 0.5) -> Dict:
        """Manually register a knowledge gap."""
        gap = KnowledgeGap(topic=topic, source="manual", urgency=urgency)
        self.gaps.append(gap)
        self.stats["total_gaps_detected"] += 1
        self._save()
        return {"gap_added": topic, "urgency": urgency}

    def get_curiosity_state(self) -> Dict:
        """Return the full curiosity state for introspection."""
        pending = [g for g in self.gaps if not g.learned]
        learned = [g for g in self.gaps if g.learned]
        return {
            "curiosity_score": round(self.curiosity_score, 3),
            "daemon_running": self.running,
            "interval_minutes": self.interval_minutes,
            "stats": self.stats,
            "pending_gaps": len(pending),
            "resolved_gaps": len(learned),
            "explored_topics": self.explored_topics[-10:],
            "pending_topics": [g.topic for g in pending[:10]],
            "recent_learning": self.learning_log[-5:],
        }

    def get_top_gaps(self, n: int = 5) -> List[Dict]:
        """Return the most urgent unresolved knowledge gaps."""
        pending = [g for g in self.gaps if not g.learned]
        pending.sort(key=lambda g: g.urgency, reverse=True)
        return [{"topic": g.topic, "urgency": g.urgency, "source": g.source}
                for g in pending[:n]]

    # ──────────────────────────────────────────────────────────────────────────
    #  PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save(self):
        os.makedirs("memory", exist_ok=True)
        try:
            with open(PERSIST_FILE, "w") as f:
                json.dump({
                    "curiosity_score": self.curiosity_score,
                    "stats": self.stats,
                    "gaps": [g.to_dict() for g in self.gaps[-200:]],
                    "explored_topics": self.explored_topics[-200:],
                    "learning_log": self.learning_log[-50:],
                }, f, indent=2)
        except Exception:
            pass

    def _load(self):
        if not os.path.exists(PERSIST_FILE):
            return
        try:
            with open(PERSIST_FILE, "r") as f:
                data = json.load(f)
            self.curiosity_score = data.get("curiosity_score", 0.5)
            self.stats.update(data.get("stats", {}))
            self.gaps = [KnowledgeGap.from_dict(g) for g in data.get("gaps", [])]
            self.explored_topics = data.get("explored_topics", [])
            self.learning_log = data.get("learning_log", [])
        except Exception:
            pass
