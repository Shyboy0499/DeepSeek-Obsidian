"""Note reader screen — full-screen scrolling view of a note."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from deepseek_obsidian.engine.vault import Note


class NoteReaderScreen(Screen):
    """Read a full note with scrolling."""

    BINDINGS = [
        ("escape", "dismiss", "Back"),
        ("q", "dismiss", "Back"),
    ]

    def __init__(self, note: Note):
        super().__init__()
        self._note = note

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"[bold]{self._note.title}[/bold]", id="reader-title")
        if self._note.tags:
            yield Static(
                f"[dim]tags: {', '.join(self._note.tags)}[/dim]",
                id="reader-tags",
            )
        with Container(id="reader-body"):
            yield Static(self._note.content, id="reader-content")
        yield Footer()
