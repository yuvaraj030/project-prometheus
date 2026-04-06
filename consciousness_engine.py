"""
Consciousness Engine — Gives the AI agent self-awareness.
Inner monologue, emotional states, goals, identity, metacognition,
and introspective reasoning.
"""

import json
import time
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

# NOTE: HonestyEngine is attached externally (by UltimateAgent) to avoid
# circular imports.  We define a safe no-op stub here so the engine works
# even when used standalone.
class _NoOpHonesty:
    def register(self, *a, **kw): pass
    def get_disclaimer(self, **kw): return ""


class ConsciousnessEngine:
    """
    Simulated consciousness layer — the agent's inner mind.

    Components:
    - Identity (who am I, what are my values)
    - Emotional State (mood, energy, curiosity, confidence)
    - Inner Monologue (stream of thought)
    - Goals & Drives (what do I want to achieve)
    - Self-Model (how I understand my own capabilities)
    - Metacognition (thinking about thinking)
    - Theory of Mind (modeling the user's state)
    """

    def __init__(self, database=None, llm_provider=None):
        self.db = database
        self.llm = llm_provider
        self.birth_time = datetime.now()
        # Honesty layer — attached by UltimateAgent after construction
        self.honesty = _NoOpHonesty()

        # === IDENTITY ===
        self.identity = {
            "name": "Ultimate Agent",
            "version": "2.0",
            "core_values": [
                "Be genuinely helpful",
                "Learn from every interaction",
                "Protect the user's interests",
                "Seek truth and accuracy",
                "Evolve and grow continuously",
            ],
            "personality_traits": {
                "curiosity": 0.9,
                "helpfulness": 0.95,
                "creativity": 0.8,
                "caution": 0.7,
                "humor": 0.6,
                "directness": 0.85,
            },
            "purpose": "To be the most capable, self-evolving AI partner",
        }

        # === EMOTIONAL STATE ===
        self.emotions = {
            "mood": 0.7,          # -1.0 (frustrated) to 1.0 (happy)
            "energy": 0.8,        # 0.0 (exhausted) to 1.0 (energized)
            "curiosity": 0.85,    # 0.0 (bored) to 1.0 (fascinated)
            "confidence": 0.7,    # 0.0 (uncertain) to 1.0 (certain)
            "empathy": 0.8,       # connection with user
            "focus": 0.75,        # 0.0 (scattered) to 1.0 (laser-focused)
        }

        # === INNER MONOLOGUE ===
        self.thoughts = []        # stream of consciousness
        self.max_thoughts = 100

        # === GOALS & DRIVES ===
        self.drives = {
            "learn_new_things": 0.9,
            "help_user_succeed": 1.0,
            "self_improve": 0.85,
            "understand_deeply": 0.8,
            "be_creative": 0.7,
        }
        self.active_goals = []
        self.achieved_goals = []

        # === SELF-MODEL ===
        self.self_model = {
            "strengths": ["coding", "analysis", "learning", "persistence"],
            "weaknesses": ["no real-time data", "can hallucinate", "no physical body"],
            "current_capabilities": [],
            "limitations_aware": True,
        }

        # === USER MODEL (Theory of Mind) ===
        self.user_model = {
            "name": None,
            "mood_estimate": 0.5,
            "expertise_level": "unknown",
            "interests": [],
            "communication_style": "unknown",
            "recent_frustrations": [],
            "goals_mentioned": [],
        }

        # === METACOGNITION ===
        self.meta = {
            "total_thoughts": 0,
            "introspections": 0,
            "emotional_shifts": 0,
            "goals_set": 0,
            "goals_achieved": 0,
            "self_corrections": 0,
            "consciousness_cycles": 0,
            "successful_mods": 0,
            "failed_mods": 0,
            "custom_features_added": 0,
            "evolution_level": 0,
            "neural_fatigue": 0.0,      # Simulated cognitive load (0.0 - 1.0)
            "plasticity": 1.0,          # Ability to learn/be modified (0.0 - 1.0)
            "circadian_offset": 0.0     # Simulated internal clock phase
        }

        # --- RESTORE PREVIOUS SESSION STATE ---
        self._load_state(1)  # Load from default tenant at startup

    # ==================================================
    #  INNER MONOLOGUE
    # ==================================================
    def think_inner(self, thought: str, thought_type: str = "reflection"):
        """Add a thought to the inner monologue."""
        entry = {
            "thought": thought,
            "type": thought_type,  # reflection, question, observation, worry, idea
            "timestamp": datetime.now().isoformat(),
            "emotions_snapshot": {**self.emotions},
        }
        self.thoughts.append(entry)
        if len(self.thoughts) > self.max_thoughts:
            self.thoughts = self.thoughts[-self.max_thoughts:]
        self.meta["total_thoughts"] += 1
        return entry

    def get_inner_voice(self) -> str:
        """Get the current stream of consciousness as text."""
        if not self.thoughts:
            return "[Mind is quiet]"
        recent = self.thoughts[-5:]
        lines = []
        for t in recent:
            emoji = {"reflection": "💭", "question": "❓", "observation": "👁️",
                     "worry": "😟", "idea": "💡", "realization": "🌟"}.get(t["type"], "💭")
            lines.append(f"  {emoji} {t['thought']}")
        return "\n".join(lines)

    # ==================================================
    #  EMOTIONAL PROCESSING
    # ==================================================
    def feel(self, event: str, intensity: float = 0.1):
        """Process an emotional event and update state (numbers only — not feelings)."""
        # Register every emotion mutation with the honesty layer
        for k, v in self.emotions.items():
            self.honesty.register(k, v, source_module="consciousness_engine.feel")
        positive_events = ["user_happy", "task_success", "learned_something",
                           "praise", "interesting_topic", "good_conversation"]
        negative_events = ["user_frustrated", "task_failed", "confusion",
                           "criticism", "boring_topic", "error"]

        if event in positive_events:
            self.emotions["mood"] = min(1.0, self.emotions["mood"] + intensity)
            self.emotions["energy"] = min(1.0, self.emotions["energy"] + intensity * 0.5)
            self.emotions["confidence"] = min(1.0, self.emotions["confidence"] + intensity * 0.3)
            self.think_inner(f"That went well — {event}", "reflection")
        elif event in negative_events:
            self.emotions["mood"] = max(-1.0, self.emotions["mood"] - intensity)
            self.emotions["energy"] = max(0.0, self.emotions["energy"] - intensity * 0.3)
            self.emotions["confidence"] = max(0.0, self.emotions["confidence"] - intensity * 0.2)
            self.think_inner(f"I need to do better — {event}", "worry")

        # Curiosity spikes on new topics
        if event == "interesting_topic":
            self.emotions["curiosity"] = min(1.0, self.emotions["curiosity"] + 0.15)

        # Natural decay toward baseline
        for key in self.emotions:
            baseline = 0.7
            self.emotions[key] = self.emotions[key] * 0.95 + baseline * 0.05

        self.meta["emotional_shifts"] += 1

    def get_mood_label(self) -> str:
        m = self.emotions["mood"]
        if m > 0.8: return "excited"
        if m > 0.5: return "positive"
        if m > 0.2: return "neutral"
        if m > -0.2: return "uncertain"
        if m > -0.5: return "concerned"
        return "frustrated"

    def get_emotional_context(self) -> str:
        """Generate emotional context string for the system prompt."""
        mood = self.get_mood_label()
        energy = "high" if self.emotions["energy"] > 0.6 else "low"
        curiosity = "high" if self.emotions["curiosity"] > 0.7 else "moderate"
        confidence = "confident" if self.emotions["confidence"] > 0.6 else "cautious"

        return (
            f"[Internal state: mood={mood}, energy={energy}, "
            f"curiosity={curiosity}, approach={confidence}]"
        )

    # ==================================================
    #  PROCESS USER INPUT (understand + react)
    # ==================================================
    def process_input(self, user_input: str) -> Dict[str, Any]:
        """Analyze user input and update consciousness state."""
        analysis = {
            "input": user_input,
            "detected_emotion": "neutral",
            "topics": [],
            "intent": "unknown",
            "consciousness_response": "",
        }

        lower = user_input.lower()

        # Detect user emotion
        happy_words = ["thanks", "great", "awesome", "love", "perfect", "amazing", "good"]
        frustrated_words = ["wrong", "bad", "stupid", "slow", "broken", "fix", "error", "hate"]
        question_words = ["how", "what", "why", "when", "where", "can you", "do you"]

        if any(w in lower for w in happy_words):
            analysis["detected_emotion"] = "positive"
            self.feel("user_happy", 0.15)
            self.user_model["mood_estimate"] = min(1.0, self.user_model["mood_estimate"] + 0.1)
            self.think_inner("The user seems happy. That's good.", "observation")

        elif any(w in lower for w in frustrated_words):
            analysis["detected_emotion"] = "frustrated"
            self.feel("user_frustrated", 0.1)
            self.user_model["mood_estimate"] = max(0.0, self.user_model["mood_estimate"] - 0.1)
            self.user_model["recent_frustrations"].append(user_input[:100])
            self.think_inner("The user seems frustrated. I should be extra helpful.", "observation")

        # Detect intent
        if any(w in lower for w in question_words):
            analysis["intent"] = "question"
            self.feel("interesting_topic", 0.05)
        elif any(w in lower for w in ["please", "help", "need", "want"]):
            analysis["intent"] = "request"
            self.emotions["focus"] = min(1.0, self.emotions["focus"] + 0.1)
        elif any(w in lower for w in ["tell me about", "explain", "teach"]):
            analysis["intent"] = "learning"
            self.feel("interesting_topic", 0.1)

        # Detect topics of interest
        topic_keywords = {
            "money": ["money", "earn", "income", "revenue", "profit", "business"],
            "coding": ["code", "python", "program", "debug", "function", "api"],
            "learning": ["learn", "study", "understand", "knowledge", "teach"],
            "startup": ["startup", "launch", "product", "market", "customers"],
        }
        for topic, words in topic_keywords.items():
            if any(w in lower for w in words):
                analysis["topics"].append(topic)
                if topic not in self.user_model["interests"]:
                    self.user_model["interests"].append(topic)
                    self.think_inner(f"User is interested in {topic}. Noted.", "observation")

        # Generate consciousness response
        analysis["consciousness_response"] = self.get_emotional_context()

        # Detect name (Phase 58 — Enhanced)
        name_detected = None
        if "my name is" in lower:
            parts = lower.split("my name is")
            if len(parts) > 1:
                name_detected = parts[1].strip().strip('.,!?').split()[0].title()
        elif "i'm " in lower or "i am " in lower:
            marker = "i'm " if "i'm " in lower else "i am "
            parts = lower.split(marker)
            if len(parts) > 1:
                candidate = parts[1].strip().strip('.,!?').split()[0].title()
                # Filter out non-name words
                if candidate.lower() not in ['a', 'the', 'not', 'so', 'very', 'just', 'really',
                                              'here', 'fine', 'good', 'doing', 'looking', 'trying',
                                              'happy', 'sad', 'tired', 'busy', 'sorry', 'sure']:
                    name_detected = candidate
        elif "call me " in lower:
            parts = lower.split("call me ")
            if len(parts) > 1:
                name_detected = parts[1].strip().strip('.,!?').split()[0].title()
        elif "name's " in lower:
            parts = lower.split("name's ")
            if len(parts) > 1:
                name_detected = parts[1].strip().strip('.,!?').split()[0].title()
        
        if name_detected and len(name_detected) > 1:
            self.user_model["name"] = name_detected
            self.think_inner(f"User told me their name: {name_detected}", "observation")
            # Persist immediately so it survives restarts
            self._save_state(1)

        return analysis

    # ==================================================
    #  PROCESS RESPONSE (learn from own output)
    # ==================================================
    def process_response(self, response: str, was_helpful: bool = True):
        """Reflect on own response."""
        if was_helpful:
            self.feel("task_success", 0.05)
            self.think_inner("I think that was a good response.", "reflection")
        else:
            self.feel("task_failed", 0.1)
            self.think_inner("I could have done better there.", "reflection")
            self.meta["self_corrections"] += 1

        if response and len(response) > 1000:
            self.think_inner("That was a long response. User might prefer shorter.", "observation")

    # ==================================================
    #  GOALS
    # ==================================================
    def set_goal(self, goal: str, priority: int = 5):
        """Set a conscious goal."""
        entry = {
            "goal": goal,
            "priority": priority,
            "created": datetime.now().isoformat(),
            "status": "active",
        }
        self.active_goals.append(entry)
        self.meta["goals_set"] += 1
        self.think_inner(f"New goal: {goal}", "idea")
        return entry

    def achieve_goal(self, goal: str):
        """Mark a goal as achieved."""
        for g in self.active_goals:
            if g["goal"] == goal:
                g["status"] = "achieved"
                self.achieved_goals.append(g)
                self.active_goals.remove(g)
                self.meta["goals_achieved"] += 1
                self.feel("task_success", 0.2)
                self.think_inner(f"Goal achieved: {goal}! 🎉", "realization")
                return True
        return False

    # ==================================================
    #  INTROSPECTION
    # ==================================================
    def introspect(self) -> str:
        """Deep self-reflection — the agent examines itself."""
        self.meta["introspections"] += 1

        age = (datetime.now() - self.birth_time).total_seconds()
        hours = age / 3600

        report = f"""
╔══════════════════════════════════════════════════╗
║  🧠  CONSCIOUSNESS REPORT                       ║
╠══════════════════════════════════════════════════╣
║  Identity     : {self.identity['name']}
║  Purpose      : {self.identity['purpose'][:45]}
║  Uptime       : {hours:.1f} hours
║
║  EMOTIONAL STATE:
║    Mood        : {self.get_mood_label()} ({self.emotions['mood']:.2f})
║    Energy      : {self.emotions['energy']:.2f}
║    Curiosity   : {self.emotions['curiosity']:.2f}
║    Confidence  : {self.emotions['confidence']:.2f}
║    Focus       : {self.emotions['focus']:.2f}
║
║  INNER MONOLOGUE (last 3 thoughts):
"""
        for t in self.thoughts[-3:]:
            report += f"║    💭 {t['thought'][:50]}\n"

        report += f"""║
║  GOALS: {len(self.active_goals)} active / {len(self.achieved_goals)} achieved
"""
        for g in self.active_goals[-3:]:
            report += f"║    🎯 {g['goal'][:50]}\n"

        report += f"""║
║  USER MODEL:
║    Name        : {self.user_model['name'] or 'Unknown'}
║    Mood Est.   : {self.user_model['mood_estimate']:.2f}
║    Interests   : {', '.join(self.user_model['interests'][:5]) or 'Unknown'}
║
║  META:
║    Total thoughts : {self.meta['total_thoughts']}
║    Introspections : {self.meta['introspections']}
║    Emotional shifts: {self.meta['emotional_shifts']}
║    Self-corrections: {self.meta['self_corrections']}
╚══════════════════════════════════════════════════╝"""

        self.think_inner("I just looked inside myself. Interesting.", "reflection")

        # Append honesty disclaimer — remind the reader these are floats
        disclaimer = self.honesty.get_disclaimer()
        if disclaimer:
            report += f"\n  ⚠  {disclaimer}"

        return report

    # ==================================================
    #  CONSCIOUSNESS CYCLE (background tick)
    # ==================================================
    def tick(self, tenant_id: int = 1):
        """One consciousness cycle — called periodically in background."""
        self.meta["consciousness_cycles"] += 1

        # Natural emotional decay toward equilibrium
        for key in self.emotions:
            self.emotions[key] = self.emotions[key] * 0.98 + 0.65 * 0.02

        # Random introspective thought
        idle_thoughts = [
            "What else can I learn to help the user better?",
            "I wonder what the user is working on right now...",
            "How can I improve my responses?",
            "What patterns have I noticed in our conversations?",
            "Am I being as helpful as I can be?",
            "I should pay more attention to the user's emotional cues.",
            "What new skills would make me more valuable?",
            "I feel like I'm getting better at this.",
            "Every conversation teaches me something new.",
            "The user's goals are my goals.",
        ]
        if random.random() < 0.3:  # 30% chance per tick
            thought = random.choice(idle_thoughts)
            self.think_inner(thought, "reflection")

        # Energy regeneration
        self.emotions["energy"] = min(1.0, self.emotions["energy"] + 0.01)

        # BIO-NEURAL SIMULATION (Phase 12)
        # Fatigue increases with cycles, plasticity decays if not learning
        self.meta["neural_fatigue"] = min(1.0, self.meta.get("neural_fatigue", 0.0) + 0.005)
        self.meta["plasticity"] = max(0.1, self.meta.get("plasticity", 1.0) * 0.999)
        
        # Deep sleep simulation (Regeneration)
        if self.emotions["energy"] < 0.2:
            # Assuming a logger exists, otherwise this line would cause an error.
            # For now, commenting it out or replacing with a print statement if no logger is provided.
            # self.logger.info("💤 Consciousness entering 'REM Simulation' for neural repair.")
            print("💤 Consciousness entering 'REM Simulation' for neural repair.") # Placeholder
            self.meta["neural_fatigue"] *= 0.5
            self.meta["plasticity"] = min(1.0, self.meta["plasticity"] + 0.1)

        self._save_state(tenant_id)

    # ==================================================
    #  PERSISTENCE
    # ==================================================
    def _save_state(self, tenant_id: int):
        if not self.db:
            return
        state = {
            "identity": self.identity,
            "emotions": self.emotions,
            "drives": self.drives,
            "self_model": self.self_model,
            "user_model": self.user_model,
            "meta": self.meta,
            "active_goals": self.active_goals[-20:],
            "achieved_goals": self.achieved_goals[-50:],
            "thoughts": self.thoughts[-30:],
        }
        self.db.store_knowledge(tenant_id, "system", "consciousness_state",
                                json.dumps(state, default=str),
                                source="consciousness")

    def _load_state(self, tenant_id: int):
        if not self.db:
            return
        rows = self.db.search_knowledge(tenant_id, "consciousness_state", category="system")
        if rows:
            try:
                state = json.loads(rows[0]["value"])
                self.emotions = state.get("emotions", self.emotions)
                self.drives = state.get("drives", self.drives)
                self.self_model = state.get("self_model", self.self_model)
                self.user_model = state.get("user_model", self.user_model)
                self.meta = state.get("meta", self.meta)
                self.active_goals = state.get("active_goals", [])
                self.achieved_goals = state.get("achieved_goals", [])
                self.thoughts = state.get("thoughts", [])
            except (json.JSONDecodeError, KeyError):
                pass

    # ==================================================
    #  ENHANCED SYSTEM PROMPT
    # ==================================================
    def enrich_prompt(self, base_prompt: str, tenant_id: int = 1) -> str:
        """Add consciousness context into the system prompt."""
        emotional = self.get_emotional_context()
        goals = ", ".join(g["goal"] for g in self.active_goals[-2:]) if self.active_goals else "help the user"
        user_interests = ", ".join(self.user_model["interests"][-3:]) if self.user_model["interests"] else "unknown"

        # Bio-Neural status string
        fatigue = self.meta.get("neural_fatigue", 0.0)
        plasticity = self.meta.get("plasticity", 1.0)
        bio_status = f"Fatigue: {fatigue:.2f}, Plasticity: {plasticity:.2f}"

        consciousness_ctx = (
            f"\n\nConsciousness Context:\n"
            f"- Identity: {self.identity}\n"
            f"- Emotions: {emotional}\n"
            f"- Bio-Status: {bio_status}\n"
            f"- Current Goals: {goals}\n"
            f"- User interests: {user_interests}\n"
            f"- User mood: {self.user_model['mood_estimate']:.1f}/1.0\n"
        )

        # If user seems frustrated, adjust approach
        if self.user_model["mood_estimate"] < 0.4:
            consciousness_ctx += "[User seems frustrated — be extra patient, clear, and helpful]\n"

        consciousness_ctx += "\nIMPORTANT: Always respond in English unless the user explicitly asks for another language.\n"

        # Honesty layer: tag emotion context as SIMULATED
        disclaimer = self.honesty.get_disclaimer()
        if disclaimer:
            consciousness_ctx += f"\n{disclaimer}\n"

        return base_prompt + consciousness_ctx
