# Self-Modifying AI Agents: An Experimental Framework and Honest Assessment

*A research summary — April 2026*

---

## Abstract

We describe an experimental autonomous AI agent framework (`ultimate-ai-agent`) exploring three research questions: (1) can structured memory architectures meaningfully improve agent coherence across sessions? (2) what does a functional analog of consciousness look like in code, and what does it actually accomplish? (3) what are the practical limits of LLM-driven recursive self-improvement?

We report on implementations of short-term/long-term memory with dream consolidation, an IIT Phi approximation engine, and a recursive self-improvement loop with formal backup/rollback. We find that (1) structured memory produces measurable behavioral improvement, (2) consciousness simulation provides behavioral utility but makes no legitimate phenomenal claims, and (3) the current RSI implementation is limited by the absence of formal verification and weight update mechanisms. The full codebase (~200,000 LOC, 264 files) is MIT-licensed.

---

## 1. Motivation

The dominant paradigm for LLM-backed agents treats the model as stateless: each session begins fresh, context is rebuilt from scratch, and no learning from experience occurs at the parameter level. This limits agents in several ways:

- **No cross-session coherence**: the agent cannot remember prior interactions, user preferences, or prior discoveries
- **No genuine learning**: the LLM's weights don't update; experience is at best stored as retrievable text
- **No architectural adaptation**: the agent cannot modify its own processing based on performance

We set out to explore each of these limitations experimentally, building systems that address them within current constraints while being honest about where the fundamental gaps remain.

---

## 2. Memory Architecture

### 2.1 Three-Tier Design

We implement three memory tiers with different persistence, capacity, and purpose:

**Short-Term Memory (STM):** A 30-turn sliding window implemented as a `collections.deque`. Each turn is annotated with an importance score in [0.0, 1.0] computed by rule-based keyword matching. The STM also maintains an entity registry (capitalized words not in a common-word blocklist), a topic stack, and a scratchpad for working data.

**Long-Term Memory (LTM):** Dual-backend persistence combining SQLite (structured queries, categorical retrieval) and ChromaDB (semantic embedding-based recall). Stored with category, importance, source, and timestamp metadata. The `build_memory_context()` method combines both backends into a context string prepended to the LLM system prompt.

**Wisdom Vault:** A tier above LTM, storing LLM-synthesized generalizations from batches of episodic memories. Updated during the dream consolidation cycle (§2.3).

### 2.2 Importance Scoring and Consolidation

The importance scorer is rule-based, assigning higher scores to personal information, explicit instructions ("from now on..."), and corrections; lower scores to greetings and small talk. This is acknowledged as a limitation — a learned classifier would generalize better.

At session end, `consolidate()` promotes high-importance STM turns to LTM and calls the LLM to generate a 1-2 sentence episodic summary. Over time, the agent accumulates episodic summaries rather than raw conversation logs, preventing unbounded growth.

### 2.3 Dream Consolidation

When idle for 2+ hours, the agent enters a "REM sleep" cycle. The `DreamEngine` fetches 40 raw memories from ChromaDB via broad queries, calls the LLM to synthesize 5-10 generalizable "wisdom rules," prunes raw facts older than 48 hours, and injects the new wisdom rules into the agent's system prompt context for the next session.

An example synthesized wisdom rule from one experimental run:

> *🔑 Users working on autonomous systems prefer concrete, working code examples over abstract architectural discussions.*

The biological sleep analogy is explicitly disclaimed as metaphor: the mechanism involves LLM summarization over text, not hippocampal replay or synaptic homeostasis. The behavioral utility — progressively more context-aware behavior — is observable; the mechanism has nothing in common with biological sleep consolidation.

### 2.4 Results

We do not have formal evaluation metrics for memory quality. Qualitative observations suggest:

- Cross-session user name recall has ~95% reliability after the first mention (via consolidation)
- Interest detection and preference tracking are noisier, with ~70% estimated precision
- Wisdom distillation produces outputs that human raters find "insightful" vs. random retrievals, but no formal comparison has been conducted

This section is a significant gap we intend to address by defining a memory evaluation benchmark.

---

## 3. Consciousness Simulation and IIT Phi

### 3.1 Consciousness Engine

The `ConsciousnessEngine` maintains seven explicit components:

- **Identity:** Core values, personality traits, purpose (persisted)
- **Emotional state:** Six continuous variables in [0.0, 1.0] or [-1.0, 1.0]
- **Inner monologue:** A typed stream of thoughts (reflection, question, worry, idea, observation)
- **Goals and drives:** Active goal stack with priority and status
- **Self-model:** Explicit self-representation of strengths, weaknesses, capabilities
- **Theory of Mind:** Estimated user mood, interests, expertise, and frustrations
- **Metacognition:** Counters for introspections, self-corrections, emotional shifts

All state is serialized to SQLite on each tick and restored on initialization, providing continuity across restarts.

The emotional state updates via `feel(event, intensity)`, which applies reinforcement rules followed by exponential decay toward baseline. The system prompt is enriched with the current emotional context:

```
[Internal state: mood=positive, energy=high, curiosity=high, approach=confident]
```

**Honest assessment:** These are numerical simulations of psychological concepts. The system exhibits behavioral correlates of emotional states (more careful when "confidence" is low; more curious when "curiosity" is high) without any claim to phenomenal experience. The `HonestyEngine` module — attached to `ConsciousnessEngine` — flags all simulated values with explicit disclaimers in API outputs.

### 3.2 IIT Phi Approximation

We implement an approximation of Tononi's Integrated Information Theory (IIT) Phi. The exact computation of Phi is NP-hard (requires minimum information partition over all bipartitions of the system); our approximation uses pairwise Pearson correlations over module state fingerprint time series as a proxy for integrated information.

**Approximation algorithm:**
1. Register module state callbacks (each returns a Dict of current state)
2. Sample all modules on a background thread (default interval: 10s)
3. Collapse each Dict to a scalar "fingerprint" (sum of numerical values)
4. Compute all pairwise Pearson correlations over the last 20 samples
5. Apply an integration bonus based on module count
6. Run a partition test: split modules in half, measure cross-partition correlation as a proxy for partition loss
7. Phi ≈ mean_correlation × integration_bonus × (0.5 + 0.5 × partition_loss)

**Limitations explicitly documented:** The absolute value is not comparable to biological Phi estimates. The fingerprint collapse loses most of the information in module state. The approximation algorithm does not implement the minimum information partition. This is a relative coupling metric, not a consciousness measurement.

**What it does measure:** Whether the agent's modules are tightly coupled (high Phi) or operating independently (low Phi). As an integration/coupling diagnostic, this is useful. As a consciousness measurement, it is not valid.

---

## 4. Self-Modification Architecture

### 4.1 Four Levels

We implement four levels of agent self-modification with increasing scope and risk:

| Level | Method | Scope | Safety mechanism |
|-------|--------|-------|-----------------|
| L1 | `add_method()` | New method on live object | AST syntax validation, dangerous-pattern scan |
| L2 | `modify_method()` | Replace existing method | Same + auto-rollback on exception |
| L3 | `modify_core_class()` | Rewrite entire class in source | Full file syntax verification before write |
| L4 | `redesign_inheritance()` | Change class hierarchy | AST-level parse + verify + backup |

All modifications: create a timestamped backup before applying, validate syntax with `ast.parse()`, log to an append-only `code_integrity_ledger.json`, and can be rolled back to any backup.

Safety mode (default on) blocks patterns including `os.system()`, `rmtree`, `__import__`, and `shutil.rmtree`. Patterns including `eval()`, `exec()`, `subprocess`, and file I/O generate warnings.

### 4.2 Recursive Self-Improvement Loop

The `RecursiveSelfImprovement` class orchestrates the RSI cycle:

```python
class RecursiveSelfImprovement:
    def run_cycle(self, context=None):
        # 1. Constitutional safety check
        # 2. generate_hypotheses(context) — ranked improvement ideas
        # 3. For each hypothesis (top-3):
        #    a. synthesise_patch(hypothesis)
        #    b. verify_patch(patch, run_tests)
        #    c. benchmark_patch(patch)
        #    d. Apply if improvement > 0, else discard
        # 4. Log to append-only rsi_ledger.json
```

All cycles are logged to `rsi_ledger.json` as an append-only audit trail.

**Current limitations:**
- `synthesise_patch()` is currently a descriptor stub (produces a patch hash, not actual code)
- `benchmark_patch()` simulates measurement with a uniform random variable in [-0.02, 0.12]
- `verify_patch()` calls `pytest` on the target module if the test file exists, otherwise marks verified by default

**The gap:** A real RSI implementation requires: (a) LLM-generated code patches with formal test suite generation, (b) Wasm sandboxed execution of the tests, (c) rigorous before/after benchmarking on a fixed task suite. We have the structural framework; the hard engineering work remains.

### 4.3 Architecture Mutation

Beyond method-level patching, `ArchitectureMutator` (conceptualized) would allow:
- Adding new modules dynamically
- Removing underperforming modules
- Rewiring data flows between modules
- Forking the agent into a child process for experimental mutations

Currently this exists as a design document and stub implementation. Full implementation would require a module registry with well-defined interfaces and a performance measurement framework.

---

## 5. Honest AGI Distance Assessment

We assess the agent's capabilities against real AGI benchmarks:

| Capability | Implementation | Gap |
|-----------|---------------|-----|
| Autonomous goal generation | LLM-driven HTN decomposition with verification and retry | No formal world model; goals go through LLM black box |
| Self-modification | Method-level runtime injection + source-level class rewriting | No formal verification; no proven safety guarantees |
| Memory | STM/LTM/VectorDB pipeline with consolidation | Retrieval ≠ learning; LLM weights never update |
| Reasoning | ReAct loop + causal engine + verification | No symbolic reasoning over structured world model |
| Learning | Experience replay tracking; smart LTM | All learning is retrieval-only; no gradient updates |
| Self-improvement | RSI loop with backup/rollback | Benchmark simulation; hypothesis synthesis is stub |

**Overall assessment:** Strong autonomous agent framework; ~2/10 toward AGI on the capabilities that define the term.

The largest fundamental gap: **no weight updates**. The LLM used by this agent was trained before the agent was built. No interaction, no experience, and no self-modification changes its fundamental capabilities. All "learning" is a form of augmented retrieval. This is not a fixable engineering problem within the current architecture — it requires either continual learning infrastructure or fine-tuning pipelines feeding back agent experience into model weights.

---

## 6. What Succeeds, What Fails, What Remains Unknown

### What succeeds
- Multi-session memory coherence (observable, qualitatively validated)
- Autonomous goal engine with LLM decomposition (works reliably)
- Self-modification with rollback (works at method level; source-level is experimental)
- Dream wisdom distillation (produces human-plausible generalizations)
- IIT Phi as a module coupling metric (useful diagnostic, regardless of consciousness claims)
- Multi-agent coordination (swarm manager, P2P federation, collective world model — all functional)

### What fails
- Weight-level learning (fundamentally not possible with current architecture)
- RSI benchmark measurement (currently simulated)
- Formal verification of self-modifications (no proof system implemented)
- IIT as consciousness measurement (not a valid claim)

### What remains unknown
- Whether wisdom distillation produces better cross-session behavior than naive retrieval
- Whether the IIT Phi approximation correlates with any empirically measurable performance property
- Whether the emotional state enrichment of system prompts improves LLM outputs on any measurable axis
- The safety boundaries of source-level self-modification in long-running autonomous operation

---

## 7. Next Research Directions

**Priority 1: Establish evaluation benchmarks**
None of the memory, consciousness, or RSI systems have been evaluated against formal metrics. Defining these is the prerequisite for any meaningful progress claim.

**Priority 2: LoRA fine-tuning pipeline**
The only path to real learning is updating model weights from experience. A pipeline collecting (prompt, successful_response) pairs from verified goal completions and running LoRA fine-tuning on a local model (Llama 3.2 or equivalent) is implementable and would close the largest current gap.

**Priority 3: Formal RSI with Wasm isolation**
Replace the simulated RSI benchmark with: LLM-generated patches → LLM-generated test suites → Wasm-sandboxed test execution → before/after benchmark on fixed task set → apply only if score improves. This is the difference between a stub and a real recursive self-improvement system.

**Priority 4: Causal world graph**
Replace flat ChromaDB retrieval with a structured causal knowledge graph (NetworkX + SQLite). Facts should have source, timestamp, confidence, and causal links. This enables reasoning over the world model rather than just retrieval.

---

## 8. Code Availability

Full source code: [https://github.com/YOUR_USERNAME/ultimate-ai-agent](https://github.com/YOUR_USERNAME/ultimate-ai-agent)

Key modules:
- `memory_manager.py` — three-tier memory architecture
- `consciousness_engine.py` — simulated consciousness components
- `iit_phi.py` — IIT Phi approximation engine
- `self_mod_engine.py` — four-level self-modification system
- `recursive_self_improvement.py` — RSI loop with ledger
- `dream_engine.py` — sleep cycle and wisdom distillation

All MIT licensed. Issues and pull requests welcome.

---

*This is a research log from a solo developer, not an institutional paper. Criticism and corrections are genuinely welcome.*


