"""Sidebar widget — referenced notes panel, search results, and note preview."""

from textual.containers import Container, Vertical
from textual.widgets import Input, ListItem, ListView, Static


class NotePreview(Vertical):
    """Shows preview content of a selected note."""

    def __init__(self):
        super().__init__()

    def compose(self):
        yield Static("[bold]📝 Preview[/bold]", classes="panel-title")
        yield Static("Select a note to preview", id="preview-content")

    def show_note(self, path: str) -> None:
        """Load and display note content from the given path."""
        preview = self.query_one("#preview-content", Static)
        try:
            content = open(path).read()
            # Show first 500 chars
            preview_text = content[:500]
            if len(content) > 500:
                preview_text += "\n..."
            preview.update(preview_text)
        except Exception:
            preview.update("[red]Cannot read note[/red]")

    def clear(self) -> None:
        self.query_one("#preview-content", Static).update(
            "Select a note to preview"
        )


class ReferencedNotesPanel(Vertical):
    """Shows which notes the AI referenced in its response."""

    def __init__(self):
        super().__init__()
        self._notes: list[tuple[str, str]] = []

    def compose(self):
        yield Static("[bold]📄 Referenced Notes[/bold]", classes="panel-title")
        yield ListView(id="notes-list")

    def set_notes(self, notes: list[tuple[str, str]]) -> None:
        """Update the list of referenced notes. Args: list of (title, path) tuples."""
        self._notes = notes
        list_view = self.query_one("#notes-list", ListView)
        list_view.clear()
        for title, path in notes:
            list_view.append(ListItem(Static(f"{title}\n    {path}")))

    def clear(self) -> None:
        list_view = self.query_one("#notes-list", ListView)
        list_view.clear()


class SearchPanel(Vertical):
    """Search bar and results for vault search."""

    def __init__(self):
        super().__init__()
        self._results: list[tuple[str, str]] = []

    def compose(self):
        yield Static("[bold]🔍 Search Vault[/bold]", classes="panel-title")
        yield Input(placeholder="Search notes...", id="search-input")
        yield ListView(id="search-results")

    def set_results(self, results: list[tuple[str, str]]) -> None:
        """Show search results. Args: list of (title, path) tuples."""
        self._results = results
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()
        for title, path in results:
            list_view.append(ListItem(Static(f"{title}\n    {path}")))

    def clear(self) -> None:
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()


class Sidebar(Container):
    """Sidebar with referenced notes, search, and preview panels."""

    def __init__(self, on_preview: callable | None = None):
        super().__init__()
        self._on_preview = on_preview

    def compose(self):
        yield ReferencedNotesPanel()
        yield SearchPanel()
        yield NotePreview()

    @property
    def notes_panel(self) -> ReferencedNotesPanel:
        return self.query_one(ReferencedNotesPanel)

    @property
    def search_panel(self) -> SearchPanel:
        return self.query_one(SearchPanel)

    @property
    def preview(self) -> NotePreview:
        return self.query_one(NotePreview)
