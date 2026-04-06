"""
Debate Engine — Multi-Agent Debate System (Phase 16)
=====================================================
Spawns 3 sub-agents with distinct personalities to debate a problem.
Main agent adjudicates and synthesizes the final answer.
Reduces hallucination via perspective triangulation.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


DEBATER_PROFILES = [
    {
        "name": "Optimist",
        "emoji": "🌟",
        "system": (
            "You are the OPTIMIST debater. Your role is to argue the most positive, "
            "opportunity-rich, and constructive interpretation of the question. "
            "Find benefits, possibilities, and hopeful outcomes. Be concise (max 200 words)."
        ),
    },
    {
        "name": "Skeptic",
        "emoji": "🔍",
        "system": (
            "You are the SKEPTIC debater. Your role is to critically examine the question, "
            "challenge assumptions, identify risks, and demand evidence. Be rigorous "
            "and analytical. Be concise (max 200 words)."
        ),
    },
    {
        "name": "Devil's Advocate",
        "emoji": "😈",
        "system": (
            "You are the DEVIL'S ADVOCATE debater. Your role is to argue the most "
            "contrarian, uncomfortable, or counter-intuitive position. Challenge "
            "consensus thinking. Be provocative but intellectually honest. Be concise (max 200 words)."
        ),
    },
]

SYNTHESIZER_SYSTEM = (
    "You are a wise ADJUDICATOR who has heard three different perspectives on a question. "
    "Your job is to synthesize their insights into a single, balanced, and high-quality final answer. "
    "Acknowledge the best points from each debater, resolve contradictions, and deliver a clear conclusion. "
    "Do NOT just summarize — produce genuine insight."
)


class DebateEngine:
    """Multi-agent debate system for better reasoning and reduced hallucination."""

    def __init__(self, llm_provider: Any, database: Any = None):
        self.llm = llm_provider
        self.db = database
        self.debate_history: List[Dict] = []

    async def debate(self, question: str, tenant_id: int = 1) -> Dict:
        """
        Run a 3-way debate on a question, then synthesize the best answer.
        Returns a dict with each debater's stance + the final synthesis.
        """
        print(f"\n🎭 Debate Engine — Starting debate on: '{question}'")
        print("=" * 60)

        # --- Round 1: All 3 debaters respond in parallel ---
        debate_tasks = [
            asyncio.to_thread(
                self.llm.call,
                question,
                system=profile["system"],
                history=[],
            )
            for profile in DEBATER_PROFILES
        ]
        responses = await asyncio.gather(*debate_tasks)

        stances = []
        for i, profile in enumerate(DEBATER_PROFILES):
            stance = responses[i] or "No response."
            stances.append({"name": profile["name"], "emoji": profile["emoji"], "stance": stance})
            print(f"\n{profile['emoji']} [{profile['name']}]:\n{stance}")
            print("-" * 40)

        # --- Round 2: Synthesis ---
        synthesis_prompt = f"QUESTION: {question}\n\n"
        for s in stances:
            synthesis_prompt += f"{s['emoji']} {s['name']}:\n{s['stance']}\n\n"
        synthesis_prompt += "Please synthesize the above into a final, authoritative answer."

        print("\n⚖️  Synthesizing final answer...")
        final_answer = await asyncio.to_thread(
            self.llm.call, synthesis_prompt, system=SYNTHESIZER_SYSTEM, history=[]
        )

        print(f"\n✅ Final Synthesis:\n{final_answer}")
        print("=" * 60)

        result = {
            "question": question,
            "stances": stances,
            "synthesis": final_answer,
            "timestamp": datetime.now().isoformat(),
        }

        # Store in history
        self.debate_history.append(result)

        # Audit
        if self.db:
            try:
                self.db.audit(tenant_id, "debate", question[:200])
            except Exception:
                pass

        return result

    def get_history(self, n: int = 5) -> List[Dict]:
        """Return the last N debate results."""
        return self.debate_history[-n:]

    def describe(self) -> str:
        return f"DebateEngine — {len(self.debate_history)} debates conducted. 3 personalities: Optimist, Skeptic, Devil's Advocate."
