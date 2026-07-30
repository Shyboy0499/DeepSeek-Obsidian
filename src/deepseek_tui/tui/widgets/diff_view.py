"""Diff view widget — displays proposed note edits inline with accept/reject."""

from textual.containers import Container, Horizontal
from textual.widgets import Static, Button


class DiffView(Container):
    """Shows a proposed edit as a diff with accept/reject buttons."""

    def __init__(
        self,
        note_title: str,
        old_text: str,
        new_text: str,
        proposal_id: str = "",
    ):
        super().__init__()
        self.note_title = note_title
        self.old_text = old_text
        self.new_text = new_text
        self.proposal_id = proposal_id
        self._accepted: bool | None = None

    def compose(self):
        yield Static(f'[bold]🤖 Proposed edit to "{self.note_title}":[/bold]')
        yield Static(f"[red]- {self.old_text}[/red]")
        yield Static(f"[green]+ {self.new_text}[/green]")
        with Horizontal(id="diff-actions"):
            yield Button("Accept", id="diff-accept", variant="success")
            yield Button("Reject", id="diff-reject", variant="error")
            yield Button("Edit Before Accepting", id="diff-edit")

    @property
    def is_accepted(self) -> bool | None:
        return self._accepted

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "diff-accept":
            self._accepted = True
        elif event.button.id == "diff-reject":
            self._accepted = False
        self.remove()
