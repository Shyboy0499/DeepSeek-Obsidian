"""Command palette — fuzzy-find and run any command."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static


class CommandPalette(ModalScreen[str]):
    """Fuzzy command finder. Returns the selected command string."""

    CSS = """
    CommandPalette {
        align: center middle;
    }
    #palette {
        width: 50;
        max-height: 60%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #palette-input {
        width: 100%;
    }
    """

    def __init__(self, commands: list[str]):
        super().__init__()
        self._all_commands = commands

    def compose(self) -> ComposeResult:
        with Container(id="palette"):
            yield Input(placeholder="Type to filter commands...", id="palette-input")
            yield ListView(id="palette-list")

    def on_mount(self) -> None:
        self.query_one("#palette-input", Input).focus()
        self._filter("")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "palette-input":
            self._filter(event.value)

    def _filter(self, query: str) -> None:
        list_view = self.query_one("#palette-list", ListView)
        list_view.clear()
        q = query.lower().strip()
        matches = [c for c in self._all_commands if q in c.lower()]
        if not matches:
            matches = [c for c in self._all_commands]
        for cmd in matches:
            list_view.append(ListItem(Static(f"/{cmd}")))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        list_view = self.query_one("#palette-list", ListView)
        if list_view.index is not None and list_view.children:
            item = list_view.children[list_view.index]
            text = str(item.children[0].render()).strip().lstrip("/")
            self.dismiss(text)
        elif event.value.strip():
            self.dismiss(event.value.strip().lstrip("/"))
