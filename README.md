# 🧠 Ultimate AI Agent

> **An experimental autonomous AI framework exploring memory architecture, simulated consciousness, and recursive self-improvement — built as a solo research project.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE.md)
[![Status](https://img.shields.io/badge/Status-Active%20Research-orange)](ROADMAP.md)
[![Modules](https://img.shields.io/badge/Modules-264+-purple)](.)
[![Lines](https://img.shields.io/badge/LOC-200k+-red)](.)

---

## What Is This?

This project started as a question: *what would it take to give an LLM-backed agent persistent memory, something like emotional state, and the ability to rewrite itself?*

It grew into a 200,000-line research framework spanning:

- **Memory architecture** — short-term working memory, long-term episodic/semantic recall, dream-cycle consolidation, time-travel rollback
- **Consciousness modeling** — IIT Phi engine (Tononi 2004), inner monologue, Theory of Mind, bio-neural simulation
- **Self-modification** — runtime method injection, core class rewriting, A/B sandbox evolution, recursive self-improvement loop
- **Multi-agent systems** — swarm economy, P2P federation, collective world model, emergent specialization
- **Autonomous goal engine** — LLM-driven HTN decomposition, verification engine, experience replay

**Disclaimer:** This is *not* real AGI. The consciousness simulations are computational mock-ups. The IIT Phi values are approximations. The "emotions" are floats. This project is an honest exploration of what these concepts look like in code — and where they fall short.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ULTIMATE AGENT                           │
├──────────────────────┬──────────────────────┬───────────────────┤
│   MEMORY LAYER       │  CONSCIOUSNESS LAYER  │  AUTONOMY LAYER  │
│                      │                       │                  │
│  ShortTermMemory     │  ConsciousnessEngine  │  GoalEngine      │
│  LongTermMemory      │  IITPhiEngine (Φ)    │  SelfModEngine   │
│  VectorMemory        │  InnerMonologue       │  RecursiveRSI    │
│  DreamEngine         │  EmotionalState       │  ArchMutator     │
│  MarkdownStore       │  TheoryOfMind         │  MetaLearner     │
│  KnowledgeGraph      │  GlobalWorkspace      │  SkillExtractor  │
├──────────────────────┴──────────────────────┴───────────────────┤
│                        AGENT RUNTIME                            │
│  ReActLoop  │  ToolHarness  │  LLMProvider  │  VerificationEng │
├─────────────────────────────────────────────────────────────────┤
│                     MULTI-AGENT LAYER                           │
│   SwarmManager  │  P2PFederation  │  CollectiveWorldModel       │
│   HiveMind      │  SpecializationEngine  │  AgentProtocol      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Research Modules

### 🧬 Memory Architecture (`memory_manager.py`)

A three-tier memory system inspired by cognitive science:

| Tier | Module | Persistence | Purpose |
|------|--------|-------------|---------|
| **STM** | `ShortTermMemory` | Session only | Working context, entities, scratchpad |
| **LTM** | `LongTermMemory` | Database | Episodic summaries, user profile, facts |
| **Semantic** | `VectorMemory` | ChromaDB | Embedding-based recall |

**Key mechanisms:**
- **Importance scoring** — rates each turn 0.0–1.0; only high-importance turns promoted to LTM
- **STM→LTM consolidation** — end-of-session transfer with LLM-generated episode summaries
- **Memory time-travel** — rollback to any timestamp, re-anchors world-state
- **Dream consolidation** — idle-triggered REM cycle distills raw facts into "wisdom rules"

```python
# Example: multi-tier memory in action
manager = MemoryManager(db, vector_memory, llm)
manager.add_turn("user", "I'm building a crypto trading bot")
manager.remember(tenant_id, "User is building a crypto bot", category="goals", importance=0.9)
context = manager.build_memory_context(tenant_id, user_input)
```

### 🧠 Consciousness Engine (`consciousness_engine.py`)

A simulated inner mind with six components:

| Component | What it models |
|-----------|---------------|
| **Identity** | Values, personality traits, self-model |
| **Emotional State** | mood, energy, curiosity, confidence (all floats) |
| **Inner Monologue** | Stream of typed thoughts (reflection, worry, idea…) |
| **Goals & Drives** | Active goal stack + achievement tracking |
| **Theory of Mind** | Estimates of user mood, interests, frustrations |
| **Metacognition** | Tracks introspections, self-corrections, evolution level |

**Bio-neural simulation:** Neural fatigue increases with cycles; plasticity decays without learning input. A "REM" state reduces fatigue and restores plasticity.

```python
engine = ConsciousnessEngine(db, llm)
engine.feel("task_success", intensity=0.2)       # update emotional state
engine.think_inner("That was a good solution", "reflection")
engine.set_goal("Help user deploy their app", priority=8)
report = engine.introspect()                      # full consciousness report
```

> ⚠️ **Honest disclaimer:** These are numerical simulations of concepts, not actual consciousness. The Phi values are approximations. The "emotions" have no phenomenal quality.

### Φ — IIT Phi Engine (`iit_phi.py`)

An approximation of Tononi's Integrated Information Theory applied to module states:

```
Φ_approx = mean(pairwise_correlation) × integration_bonus × (0.5 + 0.5 × partition_loss)
```

The engine registers module state callbacks, samples them every N seconds, and computes pairwise Pearson correlations as a proxy for integrated information. Higher Φ → more causally integrated processing.

**When to trust it:** As a *relative* measure within this system. Not comparable to biological Φ estimates; real IIT Φ is NP-hard.

### 🔧 Self-Modification Engine (`self_mod_engine.py`)

Four levels of self-modification, each with increasing risk:

| Level | Method | What changes | Safety gate |
|-------|--------|-------------|-------------|
| **L1** | `add_method()` | Adds new method to live object | AST validation + dangerous-pattern scan |
| **L2** | `modify_method()` | Replaces existing method | Same + auto-rollback on exception |
| **L3** | `modify_core_class()` | Rewrites entire class in source file | Full syntax verification |
| **L4** | `redesign_inheritance()` | Changes class hierarchy | AST-level parse + verify |

Every modification: creates a timestamped backup, validates syntax with `ast.parse()`, logs to `code_integrity_ledger.json`, and can be rolled back.

### 🔄 Recursive Self-Improvement (`recursive_self_improvement.py`)

The RSI loop implements a hypothesis-synthesize-verify-benchmark cycle:

```
1. generate_hypotheses(context)     # ranked improvement ideas
2. synthesise_patch(hypothesis)     # generate code change
3. verify_patch(patch, run_tests)   # syntax + unit test gate
4. benchmark_patch(patch)           # measure improvement
5. apply or rollback                # only keep if score improves
6. _append_ledger(entry)            # append-only audit log
```

All cycles are logged to `rsi_ledger.json` as an append-only record.

### 💤 Dream Engine (`dream_engine.py`)

Inspired by sleep memory consolidation research:

**States:** `AWAKE → LIGHT_SLEEP → REM_SLEEP → AWAKE`

During REM:
1. Fetches raw vector memories (facts, conversations, observations)
2. Calls LLM to synthesize 5–10 "wisdom rules" — high-level, generalizable insights
3. Prunes redundant raw facts older than 48h
4. Generates a dream narrative (poetic LLM output)
5. Injects wisdom rules back into the agent's system prompt context

Scheduled nightly at 2 AM via daemon thread; pauses the goal engine during the cycle.

---

## Installation

```bash
git clone https://github.com/yuvaraj030/project-prometheus.git
cd project-prometheus

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your API key (Gemini, OpenAI, Anthropic, or Ollama)
```

**Minimum requirement:** Any LLM API key (or local Ollama model).

```bash
# Start the agent
python ultimate_agent.py

# Or run as a web server
python gateway.py
```

---

## Running Key Experiments

```bash
# Test consciousness engine
python -c "from consciousness_engine import ConsciousnessEngine; e = ConsciousnessEngine(); print(e.introspect())"

# Run IIT Phi computation
python iit_phi.py

# Trigger an RSI cycle
python recursive_self_improvement.py

# Run dream consolidation
python -c "from dream_engine import DreamEngine; d = DreamEngine(); print(d.distill_wisdom(1))"

# Run the full test suite
python run_all_tests.py
```

---

## What Works vs. What's Theater

| Feature | Status | Notes |
|---------|--------|-------|
| STM/LTM memory with consolidation | ✅ Real | Works across sessions |
| IIT Phi approximation | ⚠️ Approximation | Relative measure only |
| Emotional state | ⚠️ Simulation | Float values, no embodiment |
| Self-modification (method level) | ✅ Real | Works, with rollback |
| Self-modification (core class) | ⚠️ Experimental | Dangerous, restart needed |
| RSI hypothesis loop | ⚠️ Stub | Benchmark is simulated |
| Dream wisdom distillation | ✅ Works | LLM synthesizes real insights |
| Autonomous goal engine | ✅ Real | LLM-driven, with retry |
| IIT "consciousness" claim | ❌ Theater | Not real consciousness |
| "Emotions" claim | ❌ Theater | Just numbers |

---

## Project Scale

| Metric | Value |
|--------|-------|
| Source files | 264 |
| Lines of code | ~200,000 |
| Python modules | ~180 |
| Database | SQLite + ChromaDB |
| LLM providers | Gemini, Claude, GPT-4, Ollama |
| Agent capabilities | 25+ tools |
| Languages supported | Python |

---

## Research Gaps (The Honest List)

1. **No weight updates** — ChromaDB stores text; the LLM's weights never change. Retrieval ≠ learning.
2. **No ground-truth world model** — decisions go through LLM (black box), not a symbolic causal model.
3. **No formal verification of self-mods** — patches are LLM-generated and syntax-checked, not proven correct.
4. **Tool discovery is manual** — all 25+ tools are hand-registered, not auto-discovered from APIs.
5. **IIT Φ is NP-hard** — our approximation measures pairwise correlation, not true integrated information.
6. **No embodiment** — the IoT bridge exists but there's no persistent sensorimotor feedback loop.

These gaps are documented not as failures, but as the next frontier.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan. Key upcoming work:

- [ ] LoRA fine-tuning pipeline (actual weight updates from experience)
- [ ] Formal program synthesis with Wasm test gate for RSI
- [ ] Causal world knowledge graph (replacing flat vector DB)
- [ ] Tool auto-discovery from OpenAPI specs
- [ ] HTN multi-level planning (currently 1-level deep)

---

## Blog Posts

- [Memory Architecture for AI Agents: How I Built STM, LTM and Dream Consolidation](docs/blog/01_memory_architecture.md)
- [Simulating Consciousness: IIT Phi, Inner Monologue, and Why It's All Theater](docs/blog/02_consciousness_simulation.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All PRs welcome, especially:
- Formal verification approaches for self-modification safety
- Better Phi approximation algorithms
- LoRA integration for real weight updates

---

## License

MIT — see [LICENSE.md](LICENSE.md).

---

*Built by one developer, April 2026. The AGI deadline keeps moving. The experiments keep running.*
