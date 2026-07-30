# DeepSeek-Tui

An AI-native note-taking and research assistant for the terminal, with deep [Obsidian](https://obsidian.md) vault integration.

Built with **Python + Textual**.

## What It Does

- Chat with AI about your Obsidian notes — ask questions, get summaries, find connections
- Semantic and full-text search across your vault
- AI suggests `[[wikilinks]]` between related notes
- Edit and create notes with a progressive permission system (Ask → Auto-Review → Full Access)
- Streaming markdown responses in the terminal
- Multi-provider support: DeepSeek, Anthropic (Claude), OpenAI (GPT), Ollama (local)

## Install

```bash
pip install deepseek-tui
```

Or via Homebrew (macOS):

```bash
brew tap Shyboy0499/deepseek-tui
brew install deepseek-tui
```

## Quick Start

```bash
# Set your API key
export DEEPSEEK_API_KEY="sk-..."

# Launch — auto-detects your Obsidian vault
deepseek-tui
```

## Configuration

On first launch, DeepSeek-Tui auto-detects your Obsidian vault. Config is stored at `~/.config/deepseek-tui/config.toml`.

```toml
[vault]
path = "~/Documents/Obsidian/MainVault"

[model]
provider = "deepseek"
model = "deepseek-chat"

[context]
max_notes = 10
full_text_search = true
```

## Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Cycle permission posture |
| `Ctrl+N` | Focus sidebar |
| `Ctrl+S` | Quick vault search |
| `Ctrl+B` | Toggle sidebar |
| `/` | Slash command palette |

## Design

See [docs/superpowers/specs/2026-07-30-deepseek-tui-design.md](docs/superpowers/specs/2026-07-30-deepseek-tui-design.md) for the full design specification.
