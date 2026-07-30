"""Input bar — text input with send button and command hints."""

from textual.containers import Horizontal, Container
from textual.widgets import Input, Button, Static


class CommandHints(Static):
    """Row of command hints at the bottom of the input area."""

    def __init__(self):
        super().__init__("")

    def on_mount(self) -> None:
        self.update(
            "[dim]/model  /search  /save  /clear  /help[/dim]"
        )


class InputBar(Container):
    """Input area with text field, send button, and command hints."""

    def compose(self):
        with Horizontal(id="input-row"):
            yield Input(
                placeholder="Ask about your notes... or / for commands",
                id="chat-input",
            )
            yield Button("Send", id="send-button", variant="primary")
        yield CommandHints()
