"""Sidebar widget — referenced notes panel and search results."""

from textual.containers import Container, Vertical
from textual.widgets import Input, ListItem, ListView, Static


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
    """Sidebar with referenced notes and search panels."""

    def compose(self):
        yield ReferencedNotesPanel()
        yield SearchPanel()

    @property
    def notes_panel(self) -> ReferencedNotesPanel:
        return self.query_one(ReferencedNotesPanel)

    @property
    def search_panel(self) -> SearchPanel:
        return self.query_one(SearchPanel)
