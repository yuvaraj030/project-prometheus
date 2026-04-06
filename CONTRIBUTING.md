<<<<<<< HEAD
# Contributing to Nexa Language

First off — thank you! Every contribution, no matter how small, makes Nexa better. 🙏

## Ways to Contribute

| Type | What to do |
|------|-----------|
| 🐛 Bug fix | Open an issue, then a PR |
| ✨ New feature | Open a feature request first so we can discuss |
| 📦 New package | Publish to registry.nexa-lang.dev |
| 📖 Docs | Edit `LANGUAGE_GUIDE.md` or `docs/` |
| 🧪 Tests | Add `.nexa` test files to `/tests` |
| 🌐 Translations | Translate `LANGUAGE_GUIDE.md` |

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/nexa-lang
cd nexa-lang

# 2. Install in dev mode
pip install -e ".[dev]"

# 3. Run the test suite
python -m nexa_lang test test_v27.nexa
python -m nexa_lang test test_v26.nexa
python -m nexa_lang test test_v25_phase1.nexa

# 4. Optionally build the native C VM
nexa build-vm
```

## Code Style

- Python files: `black` formatter (`pip install black; black nexa_lang/`)
- Nexa files: `nexa fmt` before committing
- All public functions must have docstrings
- New interpreter features must have corresponding test `.nexa` files

## PR Process

1. **One feature per PR** — focused PRs merge faster
2. **Tests required** — add a test case in `test_v27.nexa` or a new test file
3. **Update CHANGELOG.md** — add your entry under `[Unreleased]`
4. **CI must pass** — all 3 platform × 3 Python version combos

## Adding a New Keyword or Feature

When adding a new language feature, you typically need to touch:

| File | What to add |
|------|------------|
| `nexa_lang/lexer.py` | New token in `TT` enum + `KEYWORDS` map |
| `nexa_lang/ast_nodes.py` | New `@dataclass` node(s) |
| `nexa_lang/parser.py` | Parser handler `_parse_xxx()` + route in `_statement()` |
| `nexa_lang/interpreter.py` | Handler `_exec_XxxNode()` or `_eval_XxxNode()` |
| `test_v27.nexa` | Test case(s) for the feature |
| `nexa_lang/nexa_explain.py` | Add to `EXPLAIN_DB` |

## Publishing a Package to the Registry

```bash
# 1. Scaffold a new package
nexa new my-package --template cli
cd my-package

# 2. Add your Nexa code to main.nexa

# 3. Login (one-time)
nexa login

# 4. Publish with signature
nexa publish --sign
```

## Issue Labels

| Label | Meaning |
|-------|---------|
| `good first issue` | Perfect for new contributors |
| `help wanted` | We'd love a PR for this |
| `language-core` | Touches lexer/parser/interpreter |
| `tooling` | CLI, LSP, formatter, doc gen |
| `stdlib` | Standard library modules |
| `registry` | Package registry |
| `performance` | Speed improvements |
| `ai-features` | ML/AI-specific features |

## Community

- 💬 [Discord](https://discord.gg/nexa-lang) — #help, #contributors
- 🐦 Twitter: @nexa_lang
- 📧 Email: hello@nexa-lang.dev

## Recognition

All contributors are added to `CONTRIBUTORS.md` and the GitHub contributors page.
Significant contributions get a special role in our Discord community.
=======
# Contributing to Nexa

First off, thank you for considering contributing to Nexa! It's people like you that make Nexa a great language.

## 🌟 Where do I start?

If you are a beginner, look for issues with the label `good first issue`. We have specifically curated these to be approachable. If you need help, feel free to ask in the issue thread or on our Discord!

## 🐛 Found a Bug?

- **Ensure the bug was not already reported** by searching on GitHub under [Issues](https://github.com/nexa-lang/nexa/issues).
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/nexa-lang/nexa/issues/new/choose). Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

## ✨ Want a New Feature?

- Open a new issue with the `Feature Request` template.
- Explain **why** this feature would be useful to most Nexa users.
- Provide a hypothetical code snippet of how the feature would look in Nexa.

## 🛠️ Development Setup

1. Fork the repo and clone it locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/nexa.git
   cd nexa
   ```

2. Install dependencies (we recommend using a virtual environment):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```

3. Run the test suite to ensure everything is working:
   ```bash
   python -m pytest tests/
   ```

## 🔄 Submitting a Pull Request

1. Create a new branch: `git checkout -b my-feature-branch`
2. Make your changes and add tests for them.
3. Run the tests and the formatter:
   ```bash
   nexa check .
   nexa fmt .
   python -m pytest tests/
   ```
4. Commit your changes: `git commit -m 'Add some feature'`
5. Push to the branch: `git push origin my-feature-branch`
6. Submit a pull request!

## 🧑‍⚖️ Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md). We expect all contributors to maintain a welcoming and inclusive environment.
>>>>>>> 505371e59d95447c4de1bb675f9eb2687f79f60d
