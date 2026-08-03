"""Help screen — overlay showing all commands and keybindings."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class HelpModal(ModalScreen[None]):
    """Modal overlay showing all slash commands and keybindings."""

    CSS = """
    HelpModal {
        align: center middle;
    }

    #help-dialog {
        width: 60;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }

    #help-body {
        height: auto;
        max-height: 30;
        overflow-y: auto;
    }

    #help-footer {
        padding: 1 0;
        text-align: center;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, commands: list[str], keybindings: list[str]):
        super().__init__()
        self._commands = commands
        self._keybindings = keybindings

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static("⌨️  DeepSeek-Obsidian Help", id="help-title")
            with Container(id="help-body"):
                yield Static("[bold]Commands[/bold]")
                yield Static("\n".join(self._commands) + "\n")
                yield Static("[bold]Keybindings[/bold]")
                yield Static("\n".join(self._keybindings))
            with Container(id="help-footer"):
                yield Static("[dim]Press any key or click Close to dismiss[/dim]")
                yield Button("Close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        self.dismiss()
