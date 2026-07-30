"""Header bar — shows app title, permission posture, and vault name."""

from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static


class Header(Horizontal):
    """Top bar with title, posture indicator, and vault path."""

    posture = reactive("Ask")
    vault_name = reactive("")

    def compose(self):
        yield Static("DeepSeek-Tui", id="header-title")
        yield Static("Ask", id="header-posture")
        yield Static("", id="header-vault")

    def watch_posture(self, value: str) -> None:
        posture_label = self.query_one("#header-posture", Static)
        posture_label.update(f"[bold]{value}[/bold]")

    def watch_vault_name(self, value: str) -> None:
        vault_label = self.query_one("#header-vault", Static)
        if value:
            vault_label.update(f"📁 {value}")
