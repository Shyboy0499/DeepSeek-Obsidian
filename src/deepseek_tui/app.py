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


def main() -> None:
    app = DeepSeekTuiApp()
    app.run()


if __name__ == "__main__":
    main()
