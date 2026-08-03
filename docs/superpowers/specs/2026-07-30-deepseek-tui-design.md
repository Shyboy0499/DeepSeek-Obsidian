# DeepSeek-Obsidian Design Specification

**Date:** 2026-07-30
**Status:** Approved
**Stack:** Python + Textual (TUI) + Python core engine

## Overview

An AI-native note-taking and research assistant for the terminal, with deep Obsidian vault integration. Chat-first interface inspired by CodeWhale/DeepSeek-Obsidian but differentiated by its focus on local knowledge management rather than code generation.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   TUI Layer                       │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │
│  │ Chat View  │  │ Note Panel │  │ Search Panel│ │
│  │ (primary)  │  │ (sidebar)  │  │ (sidebar)   │ │
│  └────────────┘  └────────────┘  └─────────────┘ │
│              Textual (Python)                     │
├──────────────────────────────────────────────────┤
│                 Core Engine                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ AI Client│ │  Vault   │ │ Context Builder  │  │
│  │ (multi-  │ │  Reader  │ │ (RAG over notes) │  │
│  │ provider)│ │          │ │                  │  │
│  └──────────┘ └──────────┘ └──────────────────┘  │
├──────────────────────────────────────────────────┤
│                  Filesystem                       │
│         ~/Documents/Obsidian/Vault/               │
│             *.md  +  .obsidian/                   │
└──────────────────────────────────────────────────┘
```

- **TUI Layer** — Textual app. Chat is the dominant panel, side panels for referenced notes and search results. Slash commands and keybindings for all actions.
- **Core Engine** — Pure Python, no TUI dependency. Individually testable modules: vault reader, AI client, context builder.
- **Obsidian vault** — Read-only by default. Indexes `.md` files, parses frontmatter, resolves `[[wikilinks]]`, respects `.obsidian/` settings (excluded folders, etc.). Writing back is gated by permission posture.

## Chat & Obsidian Integration

### Message Flow

1. User types a message in the chat input
2. **Context Builder** searches the vault for relevant notes:
   - **Quick pass:** filename + frontmatter title match against query
   - **Deep pass (configurable):** full-text or embedding search across note content
   - If user mentions a `[[wikilink]]`, the linked note is always included
3. **Context is assembled** — relevant note excerpts (title + first ~500 chars) are added to the system prompt, along with recent chat history
4. **AI responds** — streaming tokens appear in chat view with markdown rendering. `[[links]]` suggested by the AI are highlighted and clickable (opens in note panel)
5. **Referenced notes** appear in the sidebar — showing which notes the AI drew from

### AI Capabilities (v1)

- Answer questions about notes
- Summarize a note or a topic across multiple notes
- Suggest `[[links]]` between notes
- Draft new note content (saved to vault on confirmation)
- Edit existing notes (gated by permission posture)

### Out of Scope (v1)

- Shell command execution
- Internet access
- VS Code extension
- Multi-agent fleet system

## Permission-Aware Note Operations

Three permission levels, cycled with `Tab`:

| Level | Operations | Requires |
|-------|-----------|----------|
| **Ask** | Search, summarize, suggest links | Always on |
| **Auto-Review** | Read + draft edits and new notes | User reviews diff, one key to accept |
| **Full Access** | Read + write freely | Every write logged to audit trail |

### Edit Flow

When the AI proposes an edit, it appears inline in the chat as a diff:

```
🤖 Proposed edit to "ML Notes":
   - "supervised learning is always better"
   + "supervised learning works well with labeled data"

   [Accept] [Reject] [Edit Before Accepting]
```

## TUI Layout

```
┌──────────────────────────────────────────────────────────┐
│ DeepSeek-Obsidian                    Ask │ [vault: research/]  │  Header bar
├────────────────────────────┬─────────────────────────────┤
│                            │                             │
│  Chat messages             │  Referenced Notes           │
│  (markdown rendered)       │  (clickable list)           │
│                            │                             │
│                            │  Search                     │
│                            │                             │
├────────────────────────────┴─────────────────────────────┤
│ > user input                                       [Send]│  Input bar
│ /model  /search  /save  /clear          Ask ◄ ► Act ► ►  │  Command hints
└──────────────────────────────────────────────────────────┘
```

### Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Cycle permission posture (Ask → Auto-Review → Full Access) |
| `Ctrl+N` | Focus sidebar (referenced notes/search) |
| `Ctrl+C` | Focus chat |
| `Ctrl+S` | Quick vault search from anywhere |
| `Ctrl+B` | Toggle sidebar visibility |
| `/` | Slash command palette |
| `!` | Shell command (opt-in, requires approval) |

## Slash Commands

| Command | Action |
|---------|--------|
| `/model [name]` | Switch AI provider/model mid-session |
| `/search <query>` | Search vault, show results in sidebar |
| `/open [[note]]` | Open a note in the sidebar panel |
| `/save [filename]` | Save last AI response as a new note |
| `/link <from> -> <to>` | Create a wikilink between two notes |
| `/vault <path>` | Switch to a different Obsidian vault |
| `/export <path>` | Export chat transcript to markdown |
| `/clear` | Clear current chat (with confirmation, option to save) |
| `/theme [name]` | Switch TUI theme on the fly |
| `/perm [ask\|review\|full]` | Set permission posture |
| `/help` | Show keybindings and commands |

## Configuration

Location: `~/.config/deepseek-obsidian/config.toml`

```toml
[vault]
path = "~/Documents/Obsidian/MainVault"
exclude_dirs = [".git", "_templates", ".trash"]

[model]
provider = "deepseek"        # deepseek, anthropic, openai, ollama
model = "deepseek-chat"

[context]
max_notes = 10
note_preview_chars = 500
full_text_search = true
incremental_index = true

[tui]
theme = "dracula"
permission_default = "ask"
sidebar_width = 35

[keybindings]
# customizable, shown with defaults
```

- API keys read from environment variables only (`DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). Never stored in config.
- Vault auto-detection on first launch: scans `~/Documents/` for `.obsidian/` directories. Prompts if multiple found, asks for path if none found.

## Provider Support (v1)

- DeepSeek
- Anthropic (Claude)
- OpenAI (GPT)
- Ollama (local models)

## Distribution

- `pyproject.toml` with `[project.scripts]` entrypoint for `deepseek-obsidian`
- CI builds macOS binaries via PyInstaller, pushed as GitHub releases
- Separate `homebrew-deepseek-obsidian` tap repo hosts the formula
- `pip install deepseek-obsidian` as an additional install path

## Development Workflow

- Small, atomic PRs — each merged automatically on green CI
- Each PR is a self-contained, testable change
- Enables easy `git bisect` if a bug is introduced
- repo: `Shyboy0499/DeepSeek-Obsidian`

## Out of Scope (Future)

- Fleet/multi-agent system
- VS Code extension
- Web interface
- Shell command execution
- Nix/Docker distribution (pip + Homebrew first)
- Plugin system
