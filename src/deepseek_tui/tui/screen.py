"""Main TUI screen with chat-primary layout."""

from textual.screen import Screen
from textual.widgets import Static


class MainScreen(Screen):
    """Primary screen: chat on the left, sidebar on the right, input at bottom."""

    def compose(self):
        yield Static("DeepSeek-Tui — Loading...")

    def on_mount(self) -> None:
        self.title = "DeepSeek-Tui"
