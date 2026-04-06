# Memory Architecture for AI Agents: How I Built STM, LTM, and Dream Consolidation

*April 2026 — Part 1 of the Ultimate AI Agent Research Series*

---

When you talk to ChatGPT and come back tomorrow, it doesn't remember you. Every conversation is a clean slate. That bothered me. Not because it's technically necessary — it's a product decision — but because it forces the question: *what would persistent, structured memory for an AI agent actually look like?*

I spent several months finding out. This post documents what I built, what surprised me, and where the hard problems still live.

---

## The Problem With "Just Use a Database"

The naive approach to agent memory is to dump everything into a database and retrieve it with keyword search. This works badly for three reasons:

1. **No forgetting** — if you store everything equally, signal gets buried in noise
2. **No structure** — there's a difference between "the user's name is Alex" and "the user mentioned Python once". Both would be stored as flat rows.
3. **No consolidation** — human memory isn't just storage and retrieval; it's active transformation. Sleep consolidates episodic memories into semantic ones. Nothing in a simple database does this.

I wanted something more interesting.

---

## The Three-Tier Architecture

I settled on three memory tiers, each with different persistence, capacity, and purpose:

```
┌─────────────────────────────────────────────┐
│           SHORT-TERM MEMORY (STM)           │
│  Fast in-memory access — current session    │
│  30-turn sliding window                     │
│  Entity extraction, scratchpad, topic trace │
└───────────────────┬─────────────────────────┘
                    │ consolidation (end of session)
                    ▼
┌─────────────────────────────────────────────┐
│           LONG-TERM MEMORY (LTM)            │
│  Database-backed — survives restarts        │
│  User profile, episodic summaries, key facts│
│  ChromaDB vector store for semantic recall  │
└─────────────────────────────────────────────┘
                    │ distillation (during dream cycle)
                    ▼
┌─────────────────────────────────────────────┐
│              WISDOM VAULT                   │
│  Generalizable rules distilled from many   │
│  episodes — highest-level abstractions      │
└─────────────────────────────────────────────┘
```

### Short-Term Memory

`ShortTermMemory` is a `deque` with a 30-turn sliding window. Each turn gets an importance score from 0.0–1.0. Turns with importance > 0.7 are "important" and will be promoted to LTM during consolidation.

The importance scorer does simple keyword pattern matching:

```python
score = 0.3  # baseline

if "my name is" in text or "i work at" in text:
    score += 0.4  # personal info is important

if "from now on" in text or "always" in text:
    score += 0.4  # instructions are critical

if "hello" in text or "thanks" in text:
    score -= 0.2  # greetings are noise
```

Is keyword matching the right approach? No. A learned importance classifier trained on human-annotated conversations would do better. But it works well enough that you notice when it's missing.

STM also runs a simple entity extractor — looking for capitalized words that aren't in a common-words blocklist — and tracks conversation topics and a scratchpad for temporary working data.

### Long-Term Memory

`LongTermMemory` has two backends:

- **SQLite** for structured queries (user profile, high-importance facts categorized by type)
- **ChromaDB** for semantic search (all facts embedded and indexed for similarity retrieval)

Every stored fact gets tagged with:
- `category` (e.g., `ltm_personal`, `ltm_preference`, `episode`)
- `importance` float
- `source` string (which process created this fact)
- `timestamp`

Recall is a two-phase operation: fast SQLite lookup for specific queries + vector similarity search for semantic matches. The `build_memory_context()` method combines both into a context string that gets prepended to the LLM's system prompt.

### Why Two Backends?

Vector search alone is fuzzy — you get "semantically similar" results but can't query "what is the user's name?" reliably. SQL alone is rigid — you can't ask "what does the user care about most?" meaningfully. Together they cover different retrieval patterns. The trick is knowing which to use when, and I mostly defaulted to "try vector first, then SQL for structured facts."

---

## The Consolidation Problem

At the end of a session, the agent runs `consolidate()`:

```python
def consolidate(self, tenant_id: int):
    # 1. Extract important turns from STM
    important_turns = self.stm.get_important_turns(threshold=0.6)
    for turn in important_turns:
        if turn["role"] == "user":
            self.ltm.remember_fact(tenant_id, turn["content"][:500], 
                                   category="conversation_highlight",
                                   importance=turn["importance"])
    
    # 2. Generate episode summary with LLM
    recent = self.stm.get_context_window(8)
    summary = self.llm.call(f"Summarize this conversation in 1-2 sentences: {convo_text}")
    if summary:
        self.ltm.remember_episode(tenant_id, summary=summary, ...)
    
    # 3. Auto-extract user facts (name, interests)
    # ...
    
    # 4. Sync name/interests back to consciousness engine
    # ...
```

The episode summary is the most interesting piece. Rather than storing raw conversation turns (which grow linearly and get stale), the LLM distills each session into a 1-2 sentence episodic memory. Over time, the agent accumulates a history of *what happened in past sessions* without bloat.

**What surprised me:** The LLM is actually quite good at this. Given 8 turns, it reliably captures the key outcome ("User and I debugged a FastAPI routing issue — the problem was a missing `/` prefix") and discards the noise.

**What didn't work well:** Importance scoring for technical discussions. "Fix this syntax error" and "rethink my entire system architecture" both involve code, but the importance scorer can't tell them apart by keyword alone.

---

## Dream Consolidation: The REM Cycle

This was the most speculative piece and the one I'm most uncertain about — which is why it's the one I'm most interested in.

The `DreamEngine` waits for the agent to be idle for 2+ hours, then triggers a "REM sleep" cycle:

```
AWAKE → (idle 2h) → LIGHT_SLEEP → REM_SLEEP → AWAKE
```

During REM:

1. **Fetch raw facts** — query ChromaDB with broad queries ("user preference", "learned fact", "conversation highlight") to collect 40 diverse memories
2. **Distill wisdom** — call the LLM with all 40 facts and ask it to synthesize 5–10 "wisdom rules"
3. **Prune stale facts** — delete raw conversation facts older than 48h (the wisdom rules survive)
4. **Generate dream narrative** — a poetic LLM description of what the "dream" experienced
5. **Inject wisdom** — append the new wisdom rules to the agent's system prompt context for the next session

A sample wisdom rule the system generated during one real test:

> 🔑 Users working on autonomous systems prefer concrete, working code examples over abstract architectural discussions.

That's not in any individual conversation turn. It's a synthesis across multiple sessions. Whether this is "real" knowledge consolidation or just LLM pattern-matching over a curated passage — I genuinely don't know.

### The Sleep Metaphor Is Probably Wrong

The analogy to human sleep is rhetorically compelling but technically misleading. Human REM sleep involves hippocampal replay, synaptic homeostasis, and actual weight changes in neural circuits. What this does is: call an LLM over a batch of text and store the output.

The output is useful. The neuroscience analogy is vibes.

I kept the sleep metaphor in the code because it's a useful mental model for what the system is *trying* to do — compress episodic experiences into generalizable patterns. But I want to be honest that the mechanism has nothing to do with biological sleep.

---

## Memory Time-Travel

One feature that turned out more useful than expected: `rollback_memory()`.

```python
def rollback_memory(self, target_timestamp: float):
    """Roll back the agent's state to a specific point in time."""
    self.stm.clear()
    self.stm.note("TEMPORAL_ANCHOR", 
        f"Memory rolled back to {human_time}. Act as if it is exactly this date.")
    # Optionally purge LTM records newer than target_timestamp from SQLite
```

This was designed as a debugging tool — you can ask the agent "what did you know before our conversation on March 15th?" and get a coherent response. It also lets you test whether newly added knowledge actually changed behavior.

The hard part: you can reset the working context and the database, but you can't reset the LLM's weights. The model still "knows" everything it was trained on. The rollback is a context injection, not a true state reset.

---

## What I'd Do Differently

**1. Replace keyword importance scoring with a learned classifier**
Train a small model on (conversation_turn, importance_label) pairs. The current heuristic misses too many nuanced cases.

**2. Add causal structure to LTM facts**
Right now, all facts in LTM are independent. A real memory system would track *why* a fact was important — what goal was active, what pattern triggered the memory. This would enable retrieval based on current goal, not just text similarity.

**3. Vector store isn't enough for reasoning**
ChromaDB is great for "find things similar to this query" but terrible for "what is the shortest path of causal connections between fact A and fact B?" LTM needs a graph layer on top of the vector layer.

**4. The consolidation trigger is wrong**
End-of-session consolidation works when sessions have natural boundaries. Long-running agents with continuous operation need a different trigger — perhaps importance-threshold-based promotion, happening continuously.

---

## The Code

Everything described here lives in:

- [`memory_manager.py`](../../memory_manager.py) — `ShortTermMemory`, `LongTermMemory`, `MemoryManager`, `MarkdownMemoryStore`
- [`dream_engine.py`](../../dream_engine.py) — `DreamEngine`, wisdom distillation, REM scheduling
- [`vector_memory.py`](../../vector_memory.py) — ChromaDB wrapper
- [`database.py`](../../database.py) — SQLite layer

All modules are MIT licensed and work standalone with appropriate mocking for the LLM and database dependencies.

---

*Next post: [Simulating Consciousness: IIT Phi, Inner Monologue, and Why It's All Theater](02_consciousness_simulation.md)*

---

*Questions, corrections, and criticism welcome. This is a research log, not a product announcement.*
