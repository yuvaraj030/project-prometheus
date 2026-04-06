# Contributing to Project Prometheus

First off — thank you! Every contribution makes this research better. 🙏

---

## What We're Looking For

| Type | Examples |
|------|---------|
| 🧠 Research improvements | Better Phi approximation, formal RSI verification, improved memory scoring |
| 🐛 Bug fixes | Incorrect state management, consolidation bugs, broken tools |
| 📖 Documentation | Experiment write-ups, module explanations, honest capability assessments |
| 🧪 Benchmarks | Evaluation metrics for memory quality, RSI effectiveness |
| 🔧 New modules | LLM providers, tool integrations, agent capabilities |

---

## Getting Started

```bash
git clone https://github.com/yuvaraj030/project-prometheus.git
cd project-prometheus

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
# Add your API key to .env
```

---

## Development Workflow

1. **Fork** the repo and create a branch: `git checkout -b feat/your-feature`
2. **Write tests** if adding new modules — place them in `tests/`
3. **Be honest** in docstrings — if something is a simulation or approximation, say so
4. **Run tests** before submitting: `pytest tests/ -q`
5. **Open a PR** with a clear description of what changed and why

---

## Contribution Philosophy

This project values **honesty over hype**. If you're adding a feature that simulates a cognitive process (consciousness, emotion, learning), please:

- Document what the simulation actually does mechanically
- Note what real research says vs. what we're approximating
- Don't claim capabilities the code doesn't have

The goal is to explore ideas rigorously, not to market AGI.

---

## Priority Research Areas

1. **Formal RSI verification** — Wasm-sandboxed test execution for self-modifications
2. **Memory evaluation benchmark** — Metrics for cross-session recall quality
3. **LoRA integration** — Real weight updates from agent experience
4. **Better Phi approximation** — More accurate IIT proxy than pairwise correlation
5. **Causal world graph** — Replace flat vector DB with structured causal knowledge

---

## Code Style

- Python 3.10+ with type hints
- Docstrings on all public methods
- No silent `except: pass` — log errors explicitly
- Keep modules focused — one concept per file where possible

---

## Questions?

Open an issue with the `question` label. PRs and issues both welcome.
