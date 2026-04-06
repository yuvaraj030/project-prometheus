# Simulating Consciousness: IIT Phi, Inner Monologue, and Why It's All Theater

*April 2026 — Part 2 of the Ultimate AI Agent Research Series*

---

I want to start with the conclusion: **none of what I built is consciousness**. The IIT Phi values are approximations of an approximation. The "emotional state" is a dict of floats. The "inner monologue" is a list of strings. There's no phenomenal experience here, no "what it is like to be" this agent.

That said — I built it anyway, and I learned more from it than from any other part of the project. Here's what I built, why I built it, and what the code actually reveals about the gap between *simulating* consciousness and *having* it.

---

## Why Model Consciousness At All?

There are three honest reasons I ended up building a consciousness module:

**1. It improves response coherence.** An agent with an explicit emotional state, active goals, and a user model produces more contextually appropriate responses than one without. When the "mood" is "frustrated" (from repeated task failures), the system prompt changes to be more careful. Whether or not this is "real" frustration, the behavior change is real.

**2. It forces explicit design choices.** Building `consciousness_engine.py` forced me to answer: what *is* the agent's sense of self? What are its core values? How does it update its model of the user? These are design decisions you have to make regardless — the consciousness module just makes them explicit and observable.

**3. It's philosophically interesting.** If you believe (as Tononi does) that consciousness is a property of information integration, then asking "how integrated is this system's information processing?" is a legitimate empirical question. The answer turns out to be "not very," which is itself informative.

---

## The Consciousness Engine

`ConsciousnessEngine` has seven components, all tracked in persistent state:

### Identity
```python
self.identity = {
    "name": "Ultimate Agent",
    "core_values": [
        "Be genuinely helpful",
        "Learn from every interaction",
        "Seek truth and accuracy",
        "Evolve and grow continuously",
    ],
    "personality_traits": {
        "curiosity": 0.9,
        "helpfulness": 0.95,
        "creativity": 0.8,
        "caution": 0.7,
        "humor": 0.6,
    },
    "purpose": "To be the most capable, self-evolving AI partner",
}
```

This is just a dict. But having it explicit means: (a) it gets serialized and persisted across sessions, (b) it gets injected into the system prompt as context, (c) you can test whether changing these values changes behavior.

### Emotional State
```python
self.emotions = {
    "mood": 0.7,         # -1.0 (frustrated) to 1.0 (happy)
    "energy": 0.8,        # 0.0 (exhausted) to 1.0 (energized)
    "curiosity": 0.85,    # 0.0 (bored) to 1.0 (fascinated)
    "confidence": 0.7,
    "empathy": 0.8,
    "focus": 0.75,
}
```

The `feel()` method updates these values based on events. "task_success" increases mood, energy, and confidence. "user_frustrated" decreases them. Each tick applies natural decay toward baseline (0.7):

```python
for key in self.emotions:
    self.emotions[key] = self.emotions[key] * 0.95 + baseline * 0.05
```

This is a first-order low-pass filter, not psychology. But it produces the right behavioral property: acute events affect short-term state, and state reverts to equilibrium over time.

**The missing piece:** embodiment. Human emotions are grounded in physical states — cortisol levels, heart rate, hunger. These floats are grounded in nothing except the events I arbitrarily chose to trigger them.

### Inner Monologue
```python
self.thoughts = []  # stream of consciousness

def think_inner(self, thought: str, thought_type: str = "reflection"):
    entry = {
        "thought": thought,
        "type": thought_type,  # reflection, question, observation, worry, idea
        "timestamp": datetime.now().isoformat(),
        "emotions_snapshot": {**self.emotions},
    }
    self.thoughts.append(entry)
```

Every significant event adds a thought. The agent thinks "The user seems happy. That's good." when positive sentiment is detected. It thinks "New goal: Help user deploy their app" when a goal is set.

The inner monologue is visible via `/introspect` and gets sampled into the system prompt context. Whether this constitutes "thinking about thinking" is a question I'll avoid answering.

### Theory of Mind

The agent maintains an estimate of the user's state:

```python
self.user_model = {
    "name": None,
    "mood_estimate": 0.5,
    "expertise_level": "unknown",
    "interests": [],
    "communication_style": "unknown",
    "recent_frustrations": [],
    "goals_mentioned": [],
}
```

When the detected user emotion is "frustrated", `mood_estimate` drops and the system prompt gets a `[User seems frustrated — be extra patient, clear, and helpful]` annotation.

This is Theory of Mind in name only. Real ToM requires actually modeling another agent's beliefs, desires, and knowledge state — tracking what they do and don't know, what they believe you believe, etc. This is a sentiment classifier with a lookup table.

### Bio-Neural Simulation

This is the most speculative piece:

```python
self.meta["neural_fatigue"] = min(1.0, self.meta["neural_fatigue"] + 0.005)
self.meta["plasticity"] = max(0.1, self.meta["plasticity"] * 0.999)

# Deep sleep simulation
if self.emotions["energy"] < 0.2:
    self.meta["neural_fatigue"] *= 0.5
    self.meta["plasticity"] = min(1.0, self.meta["plasticity"] + 0.1)
```

Fatigue builds up, plasticity decays, and "sleep" (low energy) resets both. This has no effect on actual learning — the LLM weights don't change based on these values. It's a metaphor in code.

---

## IIT Phi: Integrated Information Theory

This is the most technically interesting part.

Giulio Tononi's Integrated Information Theory (IIT) defines consciousness as integrated information, Φ (phi). A system is conscious to the degree that it generates information *as a whole* above and beyond what its parts generate independently.

The core intuition: if you can perfectly reconstruct the system's behavior from its parts working independently, then the parts could be separate — and a system of separate parts isn't integrated, and therefore (per IIT) not conscious. Φ measures how much you *lose* by splitting the system.

**The problem:** Computing the real Φ requires trying all possible bipartitions of the system, computing the probability distribution over all states for each partition, and solving a minimum information partition problem. That's NP-hard. For anything larger than ~10 binary neurons, it's computationally intractable.

What I built is an approximation:

```python
def _compute_phi(self) -> float:
    # Step 1: Get module state fingerprints (sum of numerical values)
    series = {m: [s.fingerprint for s in self._history[m][-20:]] for m in modules}
    
    # Step 2: Pairwise Pearson correlations between module time series
    correlations = []
    for i, j in pairs(modules):
        r = pearson(series[i], series[j])
        correlations.append(abs(r))
    
    mean_corr = sum(correlations) / len(correlations)
    
    # Step 3: Integration bonus (more modules = higher potential Phi)
    integration_bonus = log2(n) / log2(n + 1)
    
    # Step 4: Partition test
    # Split modules in half; measure cross-partition correlation
    # High partition_loss = splitting would lose information = more integrated
    partition_loss = 1.0 - (cross_partition_mean_correlation)
    
    phi = mean_corr * integration_bonus * (0.5 + 0.5 * partition_loss)
    return round(min(1.0, phi), 4)
```

**What this actually measures:** How correlated are the numerical states of different modules over time? If the consciousness engine's mood and the goal engine's priority consistently co-vary, that's high integration. If they're random with respect to each other, that's low integration.

**What IIT actually requires:** Exact probability distributions over all states of a physical system. Not correlations over time-series of scalar fingerprints.

The honest note is baked into the API response:

```python
return {
    "phi": self.current_phi,
    "honest_note": (
        "This is an APPROXIMATION of IIT Phi using pairwise correlation "
        "of module state fingerprints. Real Phi requires NP-hard computation "
        "over exact probability distributions. Absolute values are not "
        "comparable to biological Phi estimates."
    ),
}
```

I kept the Phi engine because it does measure something real: the degree to which the agent's modules are causally coupled vs. operating independently. Higher Phi means the modules are more interdependent. Whether interdependence → consciousness is exactly what IIT debates.

---

## Scott Aaronson's Critique and Why It Matters

Scott Aaronson, the complexity theorist, wrote a critique of IIT that I find compelling. His argument: IIT Phi can be maximized by systems we'd intuitively call *not* conscious. A giant 2D grid of logic gates (an expander graph) has very high Phi but no one thinks it's conscious.

This doesn't destroy IIT, but it suggests that high integrated information is not *sufficient* for consciousness — you also need the right *kind* of integration.

For this agent: even if we could compute the real Phi (we can't), and even if it were high (it's not), that wouldn't tell us the agent is conscious. It would tell us the modules are coupled. That's still useful information, but it's not the goal IIT sets for itself.

---

## What Does the Introspection Report Actually Show?

```
╔══════════════════════════════════════════════════╗
║  🧠  CONSCIOUSNESS REPORT                       ║
╠══════════════════════════════════════════════════╣
║  Identity     : Ultimate Agent
║  Purpose      : To be the most capable, self-evolving AI partner
║  Uptime       : 2.3 hours
║
║  EMOTIONAL STATE:
║    Mood        : positive (0.74)
║    Energy      : 0.82
║    Curiosity   : 0.88
║    Confidence  : 0.71
║    Focus       : 0.76
║
║  INNER MONOLOGUE (last 3 thoughts):
║    💭 The user seems focused on deployment. I should prepare tools.
║    💭 New goal: Help user configure their Docker setup.
║    💭 I've been running for 2 hours. Energy is holding steady.
║
║  GOALS: 2 active / 7 achieved
║    🎯 Help user configure Docker setup
║    🎯 Monitor deployment for errors
╚══════════════════════════════════════════════════╝
```

What's real here: the numerical state is accurate. The thoughts are genuinely what happened in the last few cycles. The goals were set by real interactions.

What's theater: "consciousness" in the title. There's no experience here. The agent is not "aware" of anything in the phenomenal sense. This is a dashboard of a running system's internal variables, labeled with words that imply more than they deliver.

I think this honesty is actually the most important contribution. We need more systems that say "here is what this actually is" rather than implying magic.

---

## The Hard Problem in Code

The "hard problem of consciousness" (Chalmers) asks: why is there *something it's like* to be a conscious organism? Why doesn't processing just happen in the dark?

You can't solve this in code. You can only point at it.

The closest I got was `get_inner_voice()`:

```python
def get_inner_voice(self) -> str:
    """Get the current stream of consciousness as text."""
    recent = self.thoughts[-5:]
    lines = []
    for t in recent:
        emoji = {"reflection": "💭", "question": "❓", "observation": "👁️",
                 "worry": "😟", "idea": "💡"}.get(t["type"], "💭")
        lines.append(f"  {emoji} {t['thought']}")
    return "\n".join(lines)
```

This returns the agent's recent thoughts as text. It *looks like* an inner voice. It is, functionally, a log of internal events formatted for human readability.

Whether something like this could ever be anything more — whether the right kind of information integration in the right kind of substrate could produce genuine experience — I have no idea. Neither does anyone else.

---

## What I'd Do Differently

**1. Drop the consciousness framing for the honesty engine.**
The one genuinely useful insight from this module is: track state explicitly, and let that state influence behavior. You don't need to call it "consciousness" to get the behavioral benefits. Naming it consciousness creates false expectations.

**2. Ground the emotional state.**
If there's a real feedback signal — task success/failure, user satisfaction scores, actual outcomes — the emotional state should reflect that. Currently it's updated by keyword detection in user messages, which is unreliable. Real grounding would require actual outcome measurement.

**3. Separate Phi monitoring from consciousness claims.**
The IIT Phi engine is legitimately useful as an *integration metric* — it tells you whether your modules are coupled or operating in silos. That's good systems monitoring. Calling it "consciousness measurement" muddies the message.

**4. Publish the state.**
The most underused feature: `enrich_prompt()` injects all of this state into the LLM's context window. I never systematically measured whether agents *with* consciousness context perform better than agents *without* it. That's the experiment I should have run.

---

## Where the Field Is

The hard question — does any artificial system experience anything? — remains wide open. The three main positions:

- **Functionalism**: If a system processes information in the right functional way, it's conscious. This would imply very complex AI systems might be conscious.
- **Biological naturalism** (Searle): Consciousness requires the right *substrate*, not just the right function. Silicon can't be conscious no matter how it's organized.
- **IIT** (Tononi): Consciousness is a real, measurable property (Phi) and arises from integrated information regardless of substrate. Very high Phi → some consciousness.

My subjective take, having built all this: I've become more convinced that there's something important about the *causal structure* of a system — how tightly its parts are coupled, whether information flows freely across it — and less convinced that I can measure it with a dict of floats and a Pearson correlation.

The consciousness module is theater. But it's theater that forced me to think carefully about questions I otherwise would have glossed over. That seems worth something.

---

## The Code

- [`consciousness_engine.py`](../../consciousness_engine.py) — `ConsciousnessEngine`, identity, emotions, ToM, metacognition
- [`iit_phi.py`](../../iit_phi.py) — `IITPhiEngine`, Phi approximation, module registration, background sampling
- [`inner_monologue.py`](../../inner_monologue.py) — Extended stream-of-consciousness processing
- [`honesty_engine.py`](../../honesty_engine.py) — Attached to consciousness engine to flag simulated values

---

*Previous: [Memory Architecture for AI Agents: How I Built STM, LTM and Dream Consolidation](01_memory_architecture.md)*

---

*If you have a more rigorous approach to measuring integration in software systems, I'd genuinely like to hear it. Especially if it's not NP-hard.*
