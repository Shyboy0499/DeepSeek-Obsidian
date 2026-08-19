"""Input bar — text input with send button and command hints."""

from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, Static


class CommandHints(Static):
    """Row of command hints at the bottom of the input area."""

    def __init__(self):
        super().__init__("")

    def on_mount(self) -> None:
        self.update(
            "[dim]/search /read /graph /stats /help  •  Ctrl+P palette[/dim]"
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-button":
            chat_input = self.query_one("#chat-input", Input)
            chat_input.post_message(
                Input.Submitted(chat_input, chat_input.value)
            )
