# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Default model switched from `deepseek-v4-flash` to `deepseek-v4-pro` for higher-quality answers
- Context builder now uses semantic (TF-IDF) search instead of naive keyword matching
- Note context window increased from 500 to 2000 characters per note
- API key now re-reads when switching providers

### Added

- Incremental vault refresh via mtime caching (only changed files are re-parsed)

## [0.4.0] - 2026-08-20

### Added

- Semantic search (`/search --semantic`) — find notes by meaning, not just keywords
- Command palette (`Ctrl+P`) — fuzzy-find any command
- Note graph visualization (`/graph`) — force-directed connection map
- Markdown rendering in the note reader (`/read`)
- Note management commands: `/edit`, `/delete`, `/today`, `/new`
- Tag management: `/tag add|remove`, `/tags`
- Vault statistics (`/stats`) — notes, links, broken links, tags
- Link suggestions (`/suggest-links`) — AI suggests related notes
- Backlinks (`/backlinks`) — see what links to a note
- Multiple vault support (`/vault add`, `/vault list`)
- Model persistence (saved to config)
- Chat session persistence (auto-save/restore)
- Shell command passthrough (`!command`)
- Toast notifications for system events
- Vault file watcher (auto-refresh on external changes)
- Config wizard (`/config`) — edit settings in the TUI
- Light/dark terminal detection

### Fixed

- Config corruption when saving vault path (list became string)
- Undo failed on empty-content notes
- Stale index after `/save` and `/link`
- `/open` didn't actually open the reader
- `/config` changes weren't persisted to disk
- Send button didn't work (async coroutine never awaited)
- Graph screen `q` quit the entire app instead of going back
- Permission level "ask" incorrectly said "full vault access"

## [0.3.1] - 2026-08-03

### Added

- Renamed project from `deepseek-tui` to `deepseek-obsidian`

## [0.3.0] - 2026-08-01

### Added

- Chain-of-thought reasoning display (dimmed thinking text)
- `deepseek-v4-flash` and `deepseek-v4-pro` model support
- Guided first-run setup
- Vault picker for multiple vaults
- Loading spinner during AI streaming

## [0.2.1] - 2026-07-31

### Added

- Terminal-native theming (no custom colors)
- Fast startup (removed recursive home directory scan)

## [0.2.0] - 2026-07-30

### Added

- Initial multi-provider AI client (DeepSeek, Anthropic, OpenAI, Ollama)
- Streaming markdown responses
- Permission model (Ask / Review / Full Access)
- Slash commands
- Homebrew + pip distribution
