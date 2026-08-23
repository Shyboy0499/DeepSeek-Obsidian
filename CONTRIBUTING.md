# Contributing to DeepSeek-Obsidian

Thanks for your interest in contributing! This is a note-taking and research assistant for the terminal with deep Obsidian integration.

## Getting Started

### Prerequisites

- Python 3.12+
- An Obsidian vault (any vault with a `.obsidian/` folder works)

### Development Setup

```bash
# Clone and set up
git clone git@github.com:Shyboy0499/DeepSeek-Obsidian.git
cd DeepSeek-Obsidian
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running

```bash
# With a test vault
deepseek-obsidian --vault ~/Documents/YourVault

# Set an API key to test the AI chat
export DEEPSEEK_API_KEY="sk-..."
```

### Running Tests

```bash
# Full suite (unit + integration + benchmark)
pytest -v

# Just the TUI integration tests (launch the real app)
pytest tests/integration/test_tui.py -v
```

## Project Structure

```
src/deepseek_obsidian/
├── app.py            # TUI app entry point + command handlers
├── config/           # Config loading, defaults, TOML persistence
├── engine/           # Pure Python: vault reader, AI client, context, permissions, graph
└── tui/              # Textual widgets and screens

tests/
├── test_*.py         # Unit + diagnostic + formative tests
├── benchmark/        # Performance regression tests
└── integration/      # End-to-end + real-app TUI tests
```

The `engine/` layer has **zero TUI dependency** — it's pure Python that reads/parses the vault, calls AI APIs, and builds context. The `tui/` layer is all Textual widgets and screens.

## Code Style

- Python 3.12+, type hints throughout
- Line length: 100 chars
- Lint: `ruff check src/ tests/`
- Type check: `mypy src/`
- Tests must pass: `pytest`

Run all three before submitting:

```bash
ruff check src/ tests/ && mypy src/ && pytest
```

## Making a Contribution

1. **Find or open an issue** — describe the bug or feature first
2. **Branch** off `main` — one small, focused change per PR
3. **Write tests** — every change should have test coverage
4. **Run the quality gate** — ruff + mypy + pytest
5. **Open a PR** with a clear description

We use small, atomic PRs. Each PR should do one thing and be easy to review.

## Where to Help

- **Good first issues** — search the issue tracker for `enhancement` or `bug` labels
- **Documentation** — README, config docs, command reference
- **Tests** — coverage gaps, edge cases
- **Performance** — the vault scanner and semantic search are worth profiling

## Reporting Bugs

When reporting a bug, include:

1. What you did
2. What you expected
3. What actually happened
4. Your environment (`deepseek-obsidian --version`, OS, Python version)
5. A minimal vault that reproduces it (if possible)

Thank you for contributing!
