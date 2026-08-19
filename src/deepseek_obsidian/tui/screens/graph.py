"""Graph screen — neural-network-style visualization of note connections."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, ListItem, ListView, Static

from deepseek_obsidian.engine.graph import (
    build_graph,
    force_directed_layout,
    render_graph,
)


class GraphScreen(Screen):
    """Shows a force-directed graph of notes and their wikilinks."""

    BINDINGS = [
        ("q", "dismiss", "Back"),
        ("escape", "dismiss", "Back"),
        ("r", "relayout", "Re-layout"),
        ("enter", "open_selected", "Open Note"),
    ]

    def __init__(self, vault):
        super().__init__()
        self._vault = vault
        self._width = 80
        self._height = 20
        self._draw()

    def _draw(self) -> None:
        graph = build_graph(self._vault)
        force_directed_layout(graph, self._width, self._height)
        self._graph_text = render_graph(graph, self._width, self._height)
        self._stats = (
            f"{graph.node_count} notes, {graph.edge_count} connections"
        )
        # List connected notes (degree > 0) as a selectable legend
        connected = [
            (n.title, n.degree)
            for n in graph.nodes.values() if n.degree > 0
        ]
        connected.sort(key=lambda x: -x[1])
        self._connected = connected

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="graph-container"):
            yield Static(self._graph_text, id="graph-view")
            yield Static(self._stats, id="graph-stats")
        yield Static("[bold]Connected notes (Enter to open):[/bold]", id="graph-legend")
        yield ListView(id="graph-notes", classes="graph-list")
        yield Button("Re-layout", id="relayout", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_list()

    def _populate_list(self) -> None:
        list_view = self.query_one("#graph-notes", ListView)
        list_view.clear()
        for title, degree in self._connected:
            plural = "s" if degree != 1 else ""
            label = f"{title} ({degree} link{plural})"
            list_view.append(ListItem(Static(label)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "relayout":
            self.action_relayout()

    def action_relayout(self) -> None:
        self._draw()
        self.query_one("#graph-view", Static).update(self._graph_text)
        self.query_one("#graph-stats", Static).update(self._stats)
        self._populate_list()

    def action_open_selected(self) -> None:
        list_view = self.query_one("#graph-notes", ListView)
        if list_view.index is None or list_view.index >= len(self._connected):
            return
        title = self._connected[list_view.index][0]
        note = self._vault.resolve_wikilink(title)
        if note:
            from deepseek_obsidian.tui.screens.reader import NoteReaderScreen
            self.app.push_screen(NoteReaderScreen(note))
