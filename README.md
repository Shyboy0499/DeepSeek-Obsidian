# DeepSeek-Obsidian

An AI-native note-taking and research assistant for the terminal, with deep [Obsidian](https://obsidian.md) vault integration.

Built with **Python + Textual**.

## Features

- Chat with AI about your Obsidian notes — ask questions, get summaries, find connections
- Full-text search across your vault
- AI suggests `[[wikilinks]]` between related notes
- Edit and create notes with a progressive permission system (Ask → Auto-Review → Full Access)
- Streaming markdown responses in the terminal
- Multi-provider support: DeepSeek (Chat + Reasoner), Anthropic (Claude), OpenAI (GPT), Ollama (local)
- Vault auto-detection — finds your `.obsidian/` folders automatically
- Audit trail with **Ctrl+Z** undo for all write operations
- 4 built-in themes: Dracula, Nord, Catppuccin, Monokai

## Install

```bash
# pip
pip install deepseek-obsidian

# Homebrew (macOS)
brew tap Shyboy0499/deepseek-obsidian
brew install shyboy0499/deekseek-tui/deepseek-obsidian
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
| `/model [provider] [model]` | Switch AI provider/model (e.g. `/model deepseek deepseek-reasoner`) |
| `/search <query>` | Search vault, show results in sidebar |
| `/open [[note]]` | Open a note by wikilink in the sidebar |
| `/save [filename]` | Save last AI response as a new note |
| `/link <from> -> <to>` | Create a wikilink between two notes |
| `/vault <path\|number>` | Switch to a different vault (or pick from numbered list) |
| `/export [path]` | Export chat transcript to markdown |
| `/clear [--save]` | Clear current chat (optionally save first) |
| `/theme [name]` | Switch theme (dracula, nord, catppuccin, monokai) |
| `/perm [ask\|review\|full]` | Set permission posture |
| `/help` | Show help overlay with all commands and keybindings |

## Configuration

On first launch, DeepSeek-Obsidian auto-detects your Obsidian vault. If multiple vaults are found, you'll be prompted to pick one. Config is stored at `~/.config/deepseek-obsidian/config.toml`.

```toml
[vault]
path = "~/Documents/Obsidian/MainVault"
exclude_dirs = [".git", "_templates", ".trash"]

[model]
provider = "deepseek"
model = "deepseek-chat"

[context]
max_notes = 10
note_preview_chars = 500
full_text_search = true

[tui]
theme = "dracula"
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
| DeepSeek | `deepseek-chat`, `deepseek-reasoner` |
| Anthropic | `claude-sonnet-4-6`, `claude-opus-4-8`, `claude-haiku-4-5` |
| OpenAI | `gpt-4o`, `gpt-4o-mini` |
| Ollama | `llama3`, `mistral`, `codellama`, `phi3` |

## Design

See [docs/superpowers/specs/2026-07-30-deepseek-obsidian-design.md](docs/superpowers/specs/2026-07-30-deepseek-obsidian-design.md) for the full design specification.

See [docs/superpowers/plans/2026-07-30-deepseek-obsidian-implementation.md](docs/superpowers/plans/2026-07-30-deepseek-obsidian-implementation.md) for the implementation plan.
