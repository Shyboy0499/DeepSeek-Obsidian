"""Diff view widget — displays proposed note edits inline with accept/reject/edit."""

from collections.abc import Callable

from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, Static


class DiffView(Container):
    """Shows a proposed edit as a diff with accept/reject/edit buttons.

    Calls `on_accept(new_text)` with (possibly edited) text, or `on_reject()`.
    When the user clicks "Edit Before Accepting", the new text becomes editable
    and they can modify it before applying.
    """

    def __init__(
        self,
        note_title: str,
        old_text: str,
        new_text: str,
        on_accept: Callable[[str], None] | None = None,
        on_reject: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.note_title = note_title
        self.old_text = old_text
        self.new_text = new_text
        self._on_accept = on_accept
        self._on_reject = on_reject
        self._editing = False

    def compose(self):
        yield Static(
            f'[bold]🤖 Proposed edit to "{self.note_title}":[/bold]'
        )
        yield Static(f"[red]- {self.old_text}[/red]")
        yield Static(f"[green]+ {self.new_text}[/green]", id="diff-new-text")
        with Horizontal(id="diff-actions"):
            yield Button("Accept", id="diff-accept", variant="success")
            yield Button("Edit", id="diff-edit", variant="primary")
            yield Button("Reject", id="diff-reject", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "diff-accept":
            if self._on_accept:
                self._on_accept(self.new_text)
            self.remove()
        elif event.button.id == "diff-reject":
            if self._on_reject:
                self._on_reject()
            self.remove()
        elif event.button.id == "diff-edit" and not self._editing:
            self._start_editing()
        elif event.button.id == "diff-apply" and self._editing:
            edited = self.query_one("#diff-edit-input", Input).value
            if self._on_accept:
                self._on_accept(edited)
            self.remove()
        elif event.button.id == "diff-cancel":
            # Cancel editing without rejecting
            self.remove()

    def _start_editing(self) -> None:
        self._editing = True
        # Replace static new text with editable input
        new_text_widget = self.query_one("#diff-new-text", Static)
        new_text_widget.remove()
        self.mount(Input(
            value=self.new_text,
            id="diff-edit-input",
        ), before="#diff-actions")
        # Replace buttons
        actions = self.query_one("#diff-actions", Horizontal)
        actions.remove_children()
        actions.mount(Button("Apply Edit", id="diff-apply", variant="success"))
        actions.mount(Button("Cancel", id="diff-cancel", variant="error"))
