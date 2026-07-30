"""Application entry point — wires engine to TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from deepseek_tui.config.loader import load_config
from deepseek_tui.engine.vault import VaultReader
from deepseek_tui.engine.ai_client import create_client
from deepseek_tui.engine.context import ContextBuilder
from deepseek_tui.engine.permissions import Permissions, PermissionLevel
from deepseek_tui.tui.screen import MainScreen


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
        border-left: solid $primary;
    }

    Header {
        dock: top;
        height: 1;
        background: $panel;
        padding: 0 1;
    }

    #header-title {
        width: 1fr;
    }

    #header-posture {
        width: auto;
        padding: 0 1;
        background: $accent;
    }

    #header-vault {
        width: auto;
        padding: 0 1;
    }

    InputBar {
        dock: bottom;
        height: auto;
        background: $panel;
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
        border-bottom: solid $primary;
    }

    SearchPanel {
        height: auto;
    }

    .panel-title {
        background: $boost;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("tab", "cycle_permission", "Cycle Permission"),
        ("ctrl+n", "focus_sidebar", "Focus Sidebar"),
        ("ctrl+c", "focus_chat", "Focus Chat"),
        ("ctrl+s", "quick_search", "Quick Search"),
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.permissions = Permissions(
            level=PermissionLevel.from_string(self.config.permission_default)
        )
        self.vault: VaultReader | None = None
        self.ai_client = None
        self.context_builder: ContextBuilder | None = None

    def on_mount(self) -> None:
        if self.config.vault_path and self.config.vault_path.exists():
            self._load_vault(self.config.vault_path)
        else:
            self._auto_detect_vault()

        if self.ai_client is None:
            self.ai_client = create_client(
                self.config.provider,
                self.config.model,
                api_key=self.config.api_key,
            )

        if self.vault:
            self.context_builder = ContextBuilder(
                self.vault, max_notes=self.config.max_notes
            )

        self.push_screen(MainScreen(self))
        self._command_registry = self._build_command_registry()

    def _load_vault(self, path: Path) -> None:
        self.vault = VaultReader(path, exclude_dirs=self.config.exclude_dirs)

    def _auto_detect_vault(self) -> None:
        search_paths = [
            Path.home() / "Documents",
            Path.home() / "Obsidian",
            Path.home(),
        ]
        candidates: list[Path] = []
        for search_path in search_paths:
            if search_path.exists():
                for obsidian_dir in search_path.rglob(".obsidian"):
                    vault_path = obsidian_dir.parent
                    if vault_path not in candidates:
                        candidates.append(vault_path)

        if len(candidates) == 1:
            self._load_vault(candidates[0])
        elif len(candidates) > 1:
            self._load_vault(candidates[0])

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

    def _build_command_registry(self):
        from deepseek_tui.tui.commands import Command, CommandRegistry

        registry = CommandRegistry()

        registry.register(Command(name="model", description="Switch AI provider/model", handler=self._cmd_model))
        registry.register(Command(name="search", description="Search the vault", handler=self._cmd_search))
        registry.register(Command(name="open", description="Open a note by wikilink", handler=self._cmd_open))
        registry.register(Command(name="save", description="Save last AI response as a note", handler=self._cmd_save))
        registry.register(Command(name="link", description="Create a wikilink between notes", handler=self._cmd_link))
        registry.register(Command(name="vault", description="Switch to a different vault", handler=self._cmd_vault))
        registry.register(Command(name="export", description="Export chat to markdown", handler=self._cmd_export))
        registry.register(Command(name="clear", description="Clear current chat", handler=self._cmd_clear))
        registry.register(Command(name="theme", description="Switch TUI theme", handler=self._cmd_theme))
        registry.register(Command(name="perm", description="Set permission posture", handler=self._cmd_perm))
        registry.register(Command(name="help", description="Show available commands", handler=self._cmd_help))
        return registry

    def _cmd_model(self, args: str) -> str:
        parts = args.split()
        if len(parts) >= 1:
            provider = parts[0]
            model = parts[1] if len(parts) > 1 else None
            self.config.provider = provider
            if model:
                self.config.model = model
            self.ai_client = create_client(provider, model or "deepseek-chat", api_key=self.config.api_key)
            return f"Switched to {provider}/{model or 'default'}"
        return "Usage: /model <provider> [model]"

    def _cmd_search(self, args: str) -> str:
        if not self.vault or not args:
            return "No vault loaded or no query provided."
        results = self.vault.search_full_text(args)
        screen = self.screen
        if isinstance(screen, MainScreen):
            notes_data = [(n.title, str(n.path)) for n in results[:20]]
            screen.sidebar.search_panel.set_results(notes_data)
        return f"Found {len(results)} notes matching '{args}'."

    def _cmd_open(self, args: str) -> str:
        if not self.vault or not args:
            return "No vault loaded or no note specified."
        link = args.strip().strip("[[").strip("]]")
        note = self.vault.resolve_wikilink(link)
        if note:
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.sidebar.notes_panel.set_notes([(note.title, str(note.path))])
            return f"Opened: {note.title}"
        return f"Note not found: {link}"

    def _cmd_save(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded."
        if not self.permissions.can_write():
            return "Cannot save: permission level is Ask. Switch to Full Access."
        screen = self.screen
        if isinstance(screen, MainScreen):
            chat_view = screen.chat_view
            # Get the last assistant message content from the chat view children
            for child in reversed(list(chat_view.children)):
                from deepseek_tui.tui.widgets.chat import ChatMessage
                if isinstance(child, ChatMessage) and child.role == "assistant":
                    content = child.content
                    break
            else:
                return "No AI response to save."
        else:
            return "No AI response to save."
        filename = args.strip() if args.strip() else "untitled.md"
        filepath = self.vault.vault_path / filename
        filepath.write_text(content)
        self.permissions.audit_trail.record("write", filename, "Created note from AI response")
        return f"Saved to {filename}"

    def _cmd_link(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded."
        if "->" not in args:
            return "Usage: /link <from> -> <to>"
        from_note, to_note = args.split("->", 1)
        from_note = from_note.strip()
        to_note = to_note.strip()
        if not self.permissions.can_write():
            return f"Would link [[{from_note}]] -> [[{to_note}]] (Full Access required)."
        note = self.vault.resolve_wikilink(from_note)
        if note:
            content = note.content + f"\n\nSee also: [[{to_note}]]"
            note.path.write_text(content)
            self.permissions.audit_trail.record("write", str(note.path), f"Added link to [[{to_note}]]")
            return f"Linked [[{from_note}]] -> [[{to_note}]]"
        return f"Note not found: {from_note}"

    def _cmd_vault(self, args: str) -> str:
        path = Path(args.strip()).expanduser()
        if path.exists() and (path / ".obsidian").exists():
            self._load_vault(path)
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen._update_header()
            if self.vault:
                self.context_builder = ContextBuilder(self.vault, max_notes=self.config.max_notes)
            return f"Switched to vault: {path.name}"
        return f"Not a valid Obsidian vault: {path}"

    def _cmd_export(self, args: str) -> str:
        path = Path(args.strip()).expanduser() if args.strip() else Path.home() / "deepseek-chat-export.md"
        screen = self.screen
        if isinstance(screen, MainScreen):
            lines = []
            from deepseek_tui.tui.widgets.chat import ChatMessage
            for child in screen.chat_view.children:
                if isinstance(child, ChatMessage):
                    lines.append(f"## {child.role}\n\n{child.content}\n")
            path.write_text("\n---\n".join(lines))
            return f"Chat exported to {path}"
        return "Nothing to export."

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
        available = ["dracula", "nord", "catppuccin", "monokai"]
        if theme in available:
            self.theme = theme
            return f"Theme changed to {theme}."
        return f"Available themes: {', '.join(available)}"

    def _cmd_perm(self, args: str) -> str:
        try:
            level = PermissionLevel.from_string(args.strip())
            self.permissions.set_level(level)
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.update_posture(level.value)
            return f"Permission set to: {level.value}"
        except ValueError:
            return "Usage: /perm ask|review|full"

    def _cmd_help(self, args: str) -> str:
        lines = ["Available commands:", ""]
        for cmd in self._command_registry.list_commands():
            lines.append(f"  /{cmd.name} — {cmd.description}")
        lines.extend([
            "",
            "Keybindings:",
            "  Tab — Cycle permission posture",
            "  Ctrl+N — Focus sidebar",
            "  Ctrl+C — Focus chat",
            "  Ctrl+S — Quick vault search",
            "  Ctrl+B — Toggle sidebar",
        ])
        return "\n".join(lines)


def main() -> None:
    app = DeepSeekTuiApp()
    app.run()


if __name__ == "__main__":
    main()
