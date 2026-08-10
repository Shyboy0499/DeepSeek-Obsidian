"""Application entry point — wires engine to TUI."""

from __future__ import annotations

import os
from pathlib import Path

from textual.app import App

from deepseek_obsidian.config.loader import load_config
from deepseek_obsidian.engine.ai_client import AIClient, create_client
from deepseek_obsidian.engine.context import ContextBuilder
from deepseek_obsidian.engine.permissions import PermissionLevel, Permissions
from deepseek_obsidian.engine.vault import VaultReader
from deepseek_obsidian.tui.screen import MainScreen


class DeepSeekTuiApp(App):
    """Main TUI application."""

    CSS = """
    MainScreen {
        layout: grid;
        grid-size: 1;
    }

    #main-layout {
        layout: horizontal;
        height: 1fr;
    }

    #chat-column {
        width: 1fr;
    }

    #sidebar-column {
        width: 35;
    }

    Header {
        dock: top;
        height: 1;
        padding: 0 1;
    }

    #header-title {
        width: 1fr;
    }

    #header-posture {
        width: auto;
        padding: 0 1;
        text-style: bold;
    }

    #header-vault {
        width: auto;
        padding: 0 1;
    }

    InputBar {
        dock: bottom;
        height: auto;
        padding: 0 1;
    }

    #input-row {
        height: 3;
    }

    #chat-input {
        width: 1fr;
    }

    ChatView {
        height: 1fr;
    }

    Sidebar {
        height: 1fr;
    }

    ReferencedNotesPanel {
        height: 1fr;
    }

    SearchPanel {
        height: auto;
    }

    .panel-title {
        padding: 0 1;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("tab", "cycle_permission", "Cycle Permission"),
        ("ctrl+n", "focus_sidebar", "Focus Sidebar"),
        ("ctrl+l", "focus_chat", "Focus Chat"),
        ("ctrl+s", "quick_search", "Quick Search"),
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("ctrl+z", "undo", "Undo"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, cli_vault: str | None = None):
        super().__init__()
        self.config = load_config()
        self.permissions = Permissions(
            level=PermissionLevel.from_string(self.config.permission_default)
        )
        self.vault: VaultReader | None = None
        self.ai_client: AIClient | None = None
        self.context_builder: ContextBuilder | None = None
        self._cli_vault = cli_vault
        self._vault_candidates: list[Path] = []
        self._detect_terminal_theme()

    def on_mount(self) -> None:
        self._command_registry = self._build_command_registry()
        self.push_screen(MainScreen(self))

        if self.ai_client is None:
            self.ai_client = create_client(
                self.config.provider,
                self.config.model,
                api_key=self.config.api_key,
            )

        self.call_after_refresh(self._detect_and_load_vault)

    def _detect_and_load_vault(self) -> None:
        if self._cli_vault:
            self._load_vault(Path(self._cli_vault).expanduser())
            return

        if self.config.vault_path and self.config.vault_path.exists():
            self._load_vault(self.config.vault_path)
            return

        candidates = self._find_vaults()
        if len(candidates) == 0:
            self._notify_chat(
                "No Obsidian vault found.\n"
                "Use /vault <path> to open one, or restart with --vault PATH."
            )
        elif len(candidates) == 1:
            self._load_vault(candidates[0])
        else:
            lines = [
                f"Found {len(candidates)} vaults. "
                "Use /vault with a number to pick one:"
            ]
            self._vault_candidates = candidates
            for i, path in enumerate(candidates, 1):
                lines.append(f"  [{i}] {path}")
            self._notify_chat("\n".join(lines))

    def _find_vaults(self) -> list[Path]:
        search_dirs = [
            Path.home() / "Documents",
            Path.home() / "Obsidian",
            Path.home() / "Desktop",
        ]
        candidates: list[Path] = []
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            # Direct child — most vaults are one level deep
            for child in search_dir.iterdir():
                if child.is_dir() and (child / ".obsidian").exists():
                    if child not in candidates:
                        candidates.append(child)
            # Also check search_dir itself
            if (search_dir / ".obsidian").exists():
                if search_dir not in candidates:
                    candidates.append(search_dir)
        return candidates

    def _detect_terminal_theme(self) -> None:
        """Set theme based on terminal background color.
        Uses $COLORFGBG (common in most terminals): format "fg;bg".
        0-7 = dark, 8-15 = light.
        """
        colorfgbg = os.environ.get("COLORFGBG", "")
        try:
            _, bg = colorfgbg.split(";")
            bg_val = int(bg)
        except (ValueError, IndexError):
            bg_val = 0  # default: assume dark

        if bg_val >= 7:
            self.theme = "textual-light"

    def _notify_chat(self, message: str) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.chat_view.start_assistant_message()
            screen.chat_view.stream_chunk(f"⚙️ {message}")
            screen.chat_view.finish_assistant_message()

    def _load_vault(self, path: Path) -> None:
        def _on_vault_change() -> None:
            self._notify_chat("📁 Vault changed — index refreshed.")

        if self.vault:
            self.vault.stop_watcher()

        self.vault = VaultReader(
            path,
            exclude_dirs=self.config.exclude_dirs,
            on_change=_on_vault_change,
        )
        if self.vault:
            session_path = (
                Path.home() / ".config" / "deepseek-obsidian" / "sessions"
                / f"{self.vault.vault_path.name}.json"
            )
            self.context_builder = ContextBuilder(
                self.vault, max_notes=self.config.max_notes,
                session_path=session_path,
            )
            if self.config.incremental_index:
                import asyncio
                asyncio.create_task(self.vault.start_watcher())
        note_count = len(self.vault.notes)
        lines = [
            f"📁 Vault connected: {path.name} ({note_count} notes)",
        ]
        if self.context_builder and self.context_builder.restored_count:
            lines.append(
                f"💬 Restored {self.context_builder.restored_count} "
                f"messages from last session"
            )
        if not self.config.api_key:
            provider = self.config.provider.upper()
            lines.append(
                f"⚠️  No {provider}_API_KEY set — AI chat won't work. "
                f"Export your key and restart."
            )
        lines.append(
            "Try /search to find notes, /help for all commands."
        )
        self._notify_chat("\n".join(lines))

    def action_cycle_permission(self) -> None:
        new_level = self.permissions.cycle()
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.update_posture(new_level.value)

    def action_focus_sidebar(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_sidebar()

    def action_focus_chat(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_chat()

    def action_quick_search(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_search()

    def action_toggle_sidebar(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.toggle_sidebar()

    def action_undo(self) -> None:
        entry = self.permissions.audit_trail.pop_last_write()
        if entry is None:
            self._notify_chat("Nothing to undo.")
            return

        target = Path(entry.target)
        if entry.previous_content == "__NEW_FILE__":
            # Undo a file creation — delete the file
            if target.exists():
                target.unlink()
                self._notify_chat(f"Undo: deleted {target.name}")
        elif entry.previous_content:
            # Undo a modification — restore previous content
            target.write_text(entry.previous_content)
            self._notify_chat(f"Undo: restored {target.name}")
        else:
            self._notify_chat(f"Cannot undo: no previous state saved for {target.name}")

        # Persist the updated audit trail
        self.permissions._save_audit()

        # Refresh vault if loaded
        if self.vault:
            self.vault.refresh()

    def _build_command_registry(self):
        from deepseek_obsidian.tui.commands import Command, CommandRegistry

        registry = CommandRegistry()

        registry.register(Command(
            name="model", description="Switch AI provider/model",
            handler=self._cmd_model,
        ))
        registry.register(Command(
            name="search", description="Search the vault",
            handler=self._cmd_search,
        ))
        registry.register(Command(
            name="open", description="Open a note by wikilink",
            handler=self._cmd_open,
        ))
        registry.register(Command(
            name="save", description="Save last AI response as a note",
            handler=self._cmd_save,
        ))
        registry.register(Command(
            name="link", description="Create a wikilink between notes",
            handler=self._cmd_link,
        ))
        registry.register(Command(
            name="new", description="Create a new note",
            handler=self._cmd_new,
        ))
        registry.register(Command(
            name="vault", description="Switch to a different vault",
            handler=self._cmd_vault,
        ))
        registry.register(Command(
            name="export", description="Export chat to markdown",
            handler=self._cmd_export,
        ))
        registry.register(Command(
            name="clear", description="Clear current chat",
            handler=self._cmd_clear,
        ))
        registry.register(Command(
            name="theme", description="Switch TUI theme",
            handler=self._cmd_theme,
        ))
        registry.register(Command(
            name="perm", description="Set permission posture",
            handler=self._cmd_perm,
        ))
        registry.register(Command(
            name="help", description="Show available commands",
            handler=self._cmd_help,
        ))
        return registry

    def _cmd_model(self, args: str) -> str:
        if not args.strip():
            provider = self.ai_client.provider if self.ai_client else self.config.provider
            return (
                f"Current: {provider}. "
                "Usage: /model <provider> [model]\n"
                "Providers: deepseek, anthropic, openai, ollama"
            )

        parts = args.split()
        provider_name = parts[0]
        model = parts[1] if len(parts) > 1 else None

        try:
            from deepseek_obsidian.engine.ai_client import AIProvider
            prov = AIProvider.from_string(provider_name)
            chosen_model = model or prov.default_model
            self.ai_client = create_client(
                provider_name, chosen_model,
                api_key=self.config.api_key,
            )
            self.config.provider = provider_name
            self.config.model = chosen_model
            return (
                f"Requested: {provider_name}/{chosen_model}\n"
                "Actual model confirmed on next message."
            )
        except ValueError:
            return (
                f"Unknown provider: {provider_name}. "
                "Available: deepseek, anthropic, openai, ollama"
            )

    def _cmd_search(self, args: str) -> str:
        if not self.vault or not args:
            return "No vault loaded. Use /vault <path> to open one, or restart with --vault PATH."
        results = self.vault.search_full_text(args)
        screen = self.screen
        if isinstance(screen, MainScreen):
            notes_data = [(n.title, str(n.path)) for n in results[:20]]
            screen.sidebar.search_panel.set_results(notes_data)
        return f"Found {len(results)} notes matching '{args}'."

    def _cmd_open(self, args: str) -> str:
        if not self.vault or not args:
            return "No vault loaded. Use /vault <path> to open a vault first."
        link = args.strip().strip("[[").strip("]]")
        note = self.vault.resolve_wikilink(link)
        if note:
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.sidebar.notes_panel.set_notes([(note.title, str(note.path))])
            return f"Opened: {note.title}"
        return f"Note not found: \"{link}\" — use /search to find notes by keyword"

    def _cmd_save(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        if not self.permissions.can_write():
            return (
                "Cannot save: permission is 'Ask' (read-only). "
                "Press Tab to cycle to Full Access, or use /perm full."
            )
        screen = self.screen
        if isinstance(screen, MainScreen):
            chat_view = screen.chat_view
            # Get the last assistant message content from the chat view children
            for child in reversed(list(chat_view.children)):
                from deepseek_obsidian.tui.widgets.chat import ChatMessage
                if isinstance(child, ChatMessage) and child.role == "assistant":
                    content = child.text
                    break
            else:
                return "No AI response to save. Send a message to the AI first."
        else:
            return "No AI response to save. Send a message to the AI first."
        filename = args.strip() if args.strip() else "untitled.md"
        filepath = self.vault.vault_path / filename
        filepath.write_text(str(content))
        self.permissions.record_write(
            str(filepath), "Created note from AI response",
            previous_content="__NEW_FILE__",
        )
        return f"Saved to {filename}"

    def _cmd_link(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        if "->" not in args:
            return "Usage: /link <from> -> <to>"
        from_note, to_note = args.split("->", 1)
        from_note = from_note.strip()
        to_note = to_note.strip()
        if not self.permissions.can_write():
            return f"Would link [[{from_note}]] -> [[{to_note}]] (Full Access required)."
        note = self.vault.resolve_wikilink(from_note)
        if note:
            prev = note.content
            content = prev + f"\n\nSee also: [[{to_note}]]"
            note.path.write_text(content)
            self.permissions.record_write(
                str(note.path),
                f"Added link to [[{to_note}]]",
                previous_content=prev,
            )
            return f"Linked [[{from_note}]] -> [[{to_note}]]"
        return f"Note not found: \"{from_note}\" — check the title with /search"

    def _cmd_new(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        if not self.permissions.can_write():
            return (
                "Cannot create: permission is 'Ask' (read-only). "
                "Press Tab to cycle to Full Access, or use /perm full."
            )
        title = args.strip() or "untitled"
        filename = f"{title}.md"
        filepath = self.vault.vault_path / filename
        if filepath.exists():
            return f"Note already exists: {filename}"
        content = f"# {title}\n\n"
        filepath.write_text(content)
        self.permissions.record_write(
            str(filepath), f"Created note: {title}",
            previous_content="__NEW_FILE__",
        )
        self.vault.refresh()
        return f"Created: [[{title}]]"

    def _cmd_vault(self, args: str) -> str:
        arg = args.strip()
        # Try numeric index into candidates list
        if arg.isdigit() and self._vault_candidates:
            idx = int(arg) - 1
            if 0 <= idx < len(self._vault_candidates):
                path = self._vault_candidates[idx]
                self._load_vault(path)
                self._vault_candidates = []
                screen = self.screen
                if isinstance(screen, MainScreen):
                    screen._update_header()
                return f"Switched to vault: {path.name}"
            return f"Invalid vault number. Choose 1-{len(self._vault_candidates)}."

        path = Path(arg).expanduser()
        if path.exists() and (path / ".obsidian").exists():
            self._load_vault(path)
            self._vault_candidates = []
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen._update_header()
            return f"Switched to vault: {path.name}"
        return f"Not a valid Obsidian vault (no .obsidian/ folder): {path}"

    def _cmd_export(self, args: str) -> str:
        path = (
            Path(args.strip()).expanduser() if args.strip()
            else Path.home() / "deepseek-chat-export.md"
        )
        screen = self.screen
        if isinstance(screen, MainScreen):
            lines = []
            from deepseek_obsidian.tui.widgets.chat import ChatMessage
            for child in screen.chat_view.children:
                if isinstance(child, ChatMessage):
                    lines.append(f"## {child.role}\n\n{child.text}\n")
            path.write_text("\n---\n".join(lines))
            return f"Chat exported to {path}"
        return "Nothing to export. Chat with the AI first, then use /export."

    def _cmd_clear(self, args: str) -> str:
        screen = self.screen
        if isinstance(screen, MainScreen):
            if args.strip() == "--save":
                self._cmd_export("")
            screen.chat_view.clear_chat()
            if self.context_builder:
                self.context_builder.history.clear()
            return "Chat cleared."
        return "OK"

    def _cmd_theme(self, args: str) -> str:
        theme = args.strip()
        available = [
            "dark", "light", "terminal",
            "dracula", "nord", "catppuccin", "monokai",
        ]
        if theme == "terminal" or theme == "dark":
            self.theme = "textual-dark"
            return "Theme: dark (terminal-native)."
        if theme == "light":
            self.theme = "textual-light"
            return "Theme: light."
        if theme in available:
            self.theme = theme
            return f"Theme changed to {theme}."
        return f"Available: {', '.join(available)}"

    def _cmd_perm(self, args: str) -> str:
        try:
            level = PermissionLevel.from_string(args.strip())
            self.permissions.set_level(level)
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.update_posture(level.value)
            return f"Permission set to: {level.value}"
        except ValueError:
            return "Usage: /perm ask|review|full  (or press Tab to cycle)"

    def _cmd_help(self, args: str) -> str | None:
        from deepseek_obsidian.tui.screens.help import HelpModal

        commands = [
            f"  /{cmd.name} — {cmd.description}"
            for cmd in self._command_registry.list_commands()
        ]
        keybindings = [
            "  Tab — Cycle permission posture",
            "  Ctrl+N — Focus sidebar",
            "  Ctrl+L — Focus chat",
            "  Ctrl+S — Quick vault search",
            "  Ctrl+B — Toggle sidebar",
            "  Ctrl+Z — Undo last write",
            "  Ctrl+Q — Quit",
        ]
        self.push_screen(HelpModal(commands, keybindings))
        return None


def main() -> None:
    import argparse

    from deepseek_obsidian import __version__

    parser = argparse.ArgumentParser(
        prog="deepseek-obsidian",
        description=(
            "AI-native note-taking and research assistant "
            "for the terminal with Obsidian integration."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"deepseek-obsidian {__version__}"
    )
    parser.add_argument(
        "--vault", type=str, metavar="PATH",
        help="Path to Obsidian vault (bypasses auto-detection)",
    )
    args = parser.parse_args()

    app = DeepSeekTuiApp(cli_vault=args.vault)
    app.run()


if __name__ == "__main__":
    main()
