"""Diff view widget — displays proposed note edits inline with accept/reject."""

from collections.abc import Callable

from textual.containers import Container, Horizontal
from textual.widgets import Button, Static


class DiffView(Container):
    """Shows a proposed edit as a diff with accept/reject buttons.

    Calls `on_accept` or `on_reject` callbacks when buttons are pressed.
    """

    def __init__(
        self,
        note_title: str,
        old_text: str,
        new_text: str,
        on_accept: Callable[[], None] | None = None,
        on_reject: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.note_title = note_title
        self.old_text = old_text
        self.new_text = new_text
        self._on_accept = on_accept
        self._on_reject = on_reject

    def compose(self):
        yield Static(
            f'[bold]🤖 Proposed edit to "{self.note_title}":[/bold]'
        )
        yield Static(f"[red]- {self.old_text}[/red]")
        yield Static(f"[green]+ {self.new_text}[/green]")
        with Horizontal(id="diff-actions"):
            yield Button("Accept", id="diff-accept", variant="success")
            yield Button("Reject", id="diff-reject", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "diff-accept":
            if self._on_accept:
                self._on_accept()
        elif event.button.id == "diff-reject":
            if self._on_reject:
                self._on_reject()
        self.remove()
