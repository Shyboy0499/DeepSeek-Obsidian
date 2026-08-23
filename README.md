# DeepSeek-Obsidian

An AI-native note-taking and research assistant for the terminal, with deep [Obsidian](https://obsidian.md) vault integration.

Built with **Python + Textual**.

[![CI](https://github.com/Shyboy0499/DeepSeek-Obsidian/actions/workflows/ci.yml/badge.svg)](https://github.com/Shyboy0499/DeepSeek-Obsidian/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepseek-obsidian)](https://pypi.org/project/deepseek-obsidian/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

## Features

- Chat with AI about your Obsidian notes — ask questions, get summaries, find connections
- **Semantic search** — find notes by meaning, not just keywords
- AI suggests `[[wikilinks]]` between related notes (`/suggest-links`)
- Edit and create notes with a progressive permission system (Ask → Review → Full Access)
- Streaming markdown responses with chain-of-thought reasoning
- Note graph visualization (`/graph`) — see how notes connect
- Multi-provider support: DeepSeek (V4 Flash + Pro), Anthropic (Claude), OpenAI (GPT), Ollama (local)
- Vault auto-detection + multiple vault support
- Audit trail with **Ctrl+Z** undo (persists across sessions)
- Command palette (`Ctrl+P`) — fuzzy-find any command

## Install

```bash
# pip
pip install deepseek-obsidian

# Homebrew (macOS)
brew tap Shyboy0499/deepseek-obsidian
brew install deepseek-obsidian
```

## Quick Start

```bash
# Set your API key
export DEEPSEEK_API_KEY="sk-..."

# Launch — auto-detects your Obsidian vault
deepseek-obsidian

# Or specify a vault directly
deepseek-obsidian --vault ~/Documents/MyVault
```

## Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Cycle permission posture (Ask → Review → Full Access) |
| `Ctrl+P` | Command palette (fuzzy-find commands) |
| `Ctrl+N` | Focus sidebar |
| `Ctrl+L` | Focus chat input |
| `Ctrl+S` | Quick vault search |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+Z` | Undo last write operation |
| `Ctrl+Q` | Quit |
| `/` | Slash command palette |

## Commands

| Command | Action |
|---------|--------|
| `/model [provider] [model]` | Switch AI provider/model |
| `/search [flags] <query>` | Search vault (`--semantic`, `--tag`, `--from`, `--to`) |
| `/read <note>` | Read a full note (markdown rendered) |
| `/open [[note]]` | Open a note in the reader |
| `/edit <note>` | Edit a note in your `$EDITOR` |
| `/new <title>` | Create a new note |
| `/delete <note>` | Delete a note (undoable) |
| `/today` | Open/create today's daily note |
| `/tag add\|remove <note> <tag>` | Manage frontmatter tags |
| `/tags [tag]` | List all tags or filter by tag |
| `/suggest-links <note>` | Suggest wikilinks for a note |
| `/backlinks [[note]]` | Show notes linking to a note |
| `/link <from> -> <to>` | Create a wikilink between notes |
| `/graph` | Visualize note connections |
| `/stats` | Vault health statistics |
| `/vault [list\|add <path>]` | Manage vaults |
| `/export [--json] [path]` | Export chat transcript |
| `/clear [--save]` | Clear current chat |
| `/config` | Edit settings interactively |
| `/theme [dark\|light\|...]` | Switch theme |
| `/perm [ask\|review\|full]` | Set permission posture |
| `/save [filename]` | Save last AI response as a note |
| `/help` | Show help overlay |
| `!command` | Run a shell command |

## Configuration

On first launch, DeepSeek-Obsidian auto-detects your Obsidian vault. If multiple vaults are found, you'll be prompted to pick one. Config is stored at `~/.config/deepseek-obsidian/config.toml`.

```toml
[vault]
path = "~/Documents/Obsidian/MainVault"
exclude_dirs = [".git", "_templates", ".trash"]

[model]
provider = "deepseek"
model = "deepseek-v4-pro"

[context]
max_notes = 10
note_preview_chars = 2000
full_text_search = true
incremental_index = true

[tui]
theme = ""            # empty = terminal-native colors
permission_default = "ask"
sidebar_width = 35
```

API keys are read from environment variables — never stored in config:
- `DEEPSEEK_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

## Supported Models

| Provider | Models |
|----------|--------|
| DeepSeek | `deepseek-v4-pro`, `deepseek-v4-flash` |
| Anthropic | `claude-sonnet-4-6`, `claude-opus-4-8`, `claude-haiku-4-5` |
| OpenAI | `gpt-4o`, `gpt-4o-mini` |
| Ollama | `llama3`, `mistral`, `codellama`, `phi3` |

## Design

See [docs/superpowers/specs/2026-07-30-deepseek-obsidian-design.md](docs/superpowers/specs/2026-07-30-deepseek-obsidian-design.md) for the full design specification.

See [docs/superpowers/plans/2026-07-30-deepseek-obsidian-implementation.md](docs/superpowers/plans/2026-07-30-deepseek-obsidian-implementation.md) for the implementation plan.
