"""Tests for note graph engine."""

import tempfile
from pathlib import Path

import pytest

from deepseek_obsidian.engine.graph import (
    NoteGraph,
    build_graph,
    force_directed_layout,
    render_graph,
)
from deepseek_obsidian.engine.vault import VaultReader


@pytest.fixture
def linked_vault():
    """A vault with interlinked notes."""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        (vault / ".obsidian").mkdir()
        (vault / "a.md").write_text("links to [[b]] and [[c]]")
        (vault / "b.md").write_text("links to [[a]]")
        (vault / "c.md").write_text("links to [[a]] and [[d]]")
        (vault / "d.md").write_text("no links")
        (vault / "orphan.md").write_text("no links either")
        yield vault


class TestBuildGraph:
    def test_creates_node_for_every_note(self, linked_vault):
        vault = VaultReader(linked_vault)
        graph = build_graph(vault)
        assert graph.node_count == 5
        assert graph.edge_count >= 3

    def test_drops_broken_links(self, linked_vault):
        vault = VaultReader(linked_vault)
        # Add a broken link
        (linked_vault / "broken.md").write_text("links to [[nonexistent]]")
        vault.refresh()
        graph = build_graph(vault)
        # Broken link shouldn't create an edge
        for edge in graph.edges:
            assert edge.source != "nonexistent"
            assert edge.target != "nonexistent"

    def test_computes_degrees(self, linked_vault):
        vault = VaultReader(linked_vault)
        graph = build_graph(vault)
        # 'a' connects to b and c = degree 2
        assert graph.nodes["a"].degree == 2
        # 'd' connects to c = degree 1
        assert graph.nodes["d"].degree == 1
        # orphan has degree 0
        assert graph.nodes["orphan"].degree == 0


class TestLayout:
    def test_layout_keeps_nodes_in_bounds(self, linked_vault):
        vault = VaultReader(linked_vault)
        graph = build_graph(vault)
        force_directed_layout(graph, width=80, height=24)
        for node in graph.nodes.values():
            assert 1.0 <= node.x <= 78.0
            assert 1.0 <= node.y <= 22.0

    def test_single_node_centered(self):
        graph = NoteGraph()
        graph.nodes["only"] = __import__(
            "deepseek_obsidian.engine.graph", fromlist=["GraphNode"]
        ).GraphNode(title="only")
        force_directed_layout(graph, width=40, height=20)
        assert abs(graph.nodes["only"].x - 20) < 1.0
        assert abs(graph.nodes["only"].y - 10) < 1.0

    def test_layout_deterministic_with_seed(self, linked_vault):
        vault = VaultReader(linked_vault)
        g1 = build_graph(vault)
        g2 = build_graph(vault)
        force_directed_layout(g1, seed=42)
        force_directed_layout(g2, seed=42)
        for title in g1.nodes:
            assert g1.nodes[title].x == g2.nodes[title].x
            assert g1.nodes[title].y == g2.nodes[title].y


class TestRender:
    def test_render_produces_grid(self, linked_vault):
        vault = VaultReader(linked_vault)
        graph = build_graph(vault)
        force_directed_layout(graph, width=40, height=12, seed=42)
        rendered = render_graph(graph, width=40, height=12)
        lines = rendered.split("\n")
        assert len(lines) == 12
        for line in lines:
            assert len(line) <= 40

    def test_render_contains_node_markers(self, linked_vault):
        vault = VaultReader(linked_vault)
        graph = build_graph(vault)
        force_directed_layout(graph, width=40, height=12, seed=42)
        rendered = render_graph(graph, width=40, height=12)
        # At least some nodes should be visible
        assert "●" in rendered or "○" in rendered
