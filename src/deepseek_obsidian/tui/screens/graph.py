"""Graph screen — neural-network-style visualization of note connections."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from deepseek_obsidian.engine.graph import (
    build_graph,
    force_directed_layout,
    render_graph,
)


class GraphScreen(Screen):
    """Shows a force-directed graph of notes and their wikilinks."""

    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("escape", "dismiss", "Back"),
        ("r", "relayout", "Re-layout"),
    ]

    def __init__(self, vault):
        super().__init__()
        self._vault = vault
        self._width = 80
        self._height = 30
        self._draw()

    def _draw(self) -> None:
        graph = build_graph(self._vault)
        force_directed_layout(graph, self._width, self._height)
        self._graph_text = render_graph(graph, self._width, self._height)
        self._stats = (
            f"{graph.node_count} notes, {graph.edge_count} connections"
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="graph-container"):
            yield Static(self._graph_text, id="graph-view")
            yield Static(self._stats, id="graph-stats")
        yield Button("Re-layout", id="relayout", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "relayout":
            self.action_relayout()

    def action_relayout(self) -> None:
        self._draw()
        self.query_one("#graph-view", Static).update(self._graph_text)
        self.query_one("#graph-stats", Static).update(self._stats)
