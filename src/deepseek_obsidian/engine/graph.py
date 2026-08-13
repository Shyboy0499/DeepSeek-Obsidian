"""Note graph — builds a connection graph from wikilinks and lays out nodes.

Used by the /graph command to render a neural-network-style visualization
of how notes connect via [[wikilinks]].
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from deepseek_obsidian.engine.vault import VaultReader


@dataclass
class GraphNode:
    title: str
    x: float = 0.0
    y: float = 0.0
    degree: int = 0


@dataclass
class GraphEdge:
    source: str
    target: str


@dataclass
class NoteGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


def build_graph(vault: VaultReader) -> NoteGraph:
    """Build a graph from vault wikilinks.

    Every note is a node. Every [[wikilink]] is an edge. Only edges between
    two notes that exist in the vault are kept (broken links are dropped).
    """
    graph = NoteGraph()

    # Create a node for every note
    for note in vault.notes:
        graph.nodes[note.title] = GraphNode(title=note.title)

    # Create edges from wikilinks (dedupe, only keep resolved links)
    seen_edges: set[tuple[str, str]] = set()
    for note in vault.notes:
        for link in note.wikilinks():
            target = vault.resolve_wikilink(link)
            if target is None or target.title == note.title:
                continue
            # Canonical edge (undirected)
            a, b = sorted((note.title, target.title))
            pair = (a, b)
            if pair in seen_edges:
                continue
            seen_edges.add(pair)
            graph.edges.append(GraphEdge(source=pair[0], target=pair[1]))

    # Compute degree
    for edge in graph.edges:
        if edge.source in graph.nodes:
            graph.nodes[edge.source].degree += 1
        if edge.target in graph.nodes:
            graph.nodes[edge.target].degree += 1

    return graph


def force_directed_layout(
    graph: NoteGraph,
    width: int = 80,
    height: int = 24,
    iterations: int = 120,
    seed: int = 42,
) -> None:
    """Lay out nodes using a simple force-directed (spring) model.

    Connected nodes attract, all nodes repel. Produces clusters of related
    notes — the "neural network" look.
    """
    rng = random.Random(seed)
    nodes = list(graph.nodes.values())

    # Initial random positions
    for node in nodes:
        node.x = rng.uniform(0, width)
        node.y = rng.uniform(0, height)

    if len(nodes) <= 1:
        for node in nodes:
            node.x = width / 2
            node.y = height / 2
        return

    # Build adjacency set for fast lookup
    adjacency: dict[str, set[str]] = {}
    for edge in graph.edges:
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set()).add(edge.source)

    # Force-directed iteration
    repulsion = 300.0
    attraction = 0.05
    damping = 0.85

    for _ in range(iterations):
        # Compute repulsion forces (all pairs)
        forces: dict[str, tuple[float, float]] = {
            n.title: (0.0, 0.0) for n in nodes
        }
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx = a.x - b.x
                dy = a.y - b.y
                dist_sq = dx * dx + dy * dy
                if dist_sq < 1e-6:
                    dist_sq = 1e-6
                dist = math.sqrt(dist_sq)
                force = repulsion / dist_sq
                fx = (dx / dist) * force
                fy = (dy / dist) * force
                forces[a.title] = (forces[a.title][0] + fx, forces[a.title][1] + fy)
                forces[b.title] = (forces[b.title][0] - fx, forces[b.title][1] - fy)

        # Compute attraction forces (connected pairs)
        for edge in graph.edges:
            a = graph.nodes[edge.source]
            b = graph.nodes[edge.target]
            dx = b.x - a.x
            dy = b.y - a.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 1e-6:
                dist = 1e-6
            force = attraction * dist
            fx = (dx / dist) * force
            fy = (dy / dist) * force
            forces[a.title] = (forces[a.title][0] + fx, forces[a.title][1] + fy)
            forces[b.title] = (forces[b.title][0] - fx, forces[b.title][1] - fy)

        # Apply forces with damping
        for node in nodes:
            fx, fy = forces[node.title]
            node.x += fx * damping
            node.y += fy * damping
            # Clamp to bounds
            node.x = max(1.0, min(float(width - 2), node.x))
            node.y = max(1.0, min(float(height - 2), node.y))


def render_graph(
    graph: NoteGraph,
    width: int = 80,
    height: int = 24,
) -> str:
    """Render the graph as an ASCII/Unicode grid."""
    # Round node positions to grid
    grid: list[list[str]] = [
        [" " for _ in range(width)] for _ in range(height)
    ]

    # Draw edges first (behind nodes)
    for edge in graph.edges:
        a = graph.nodes[edge.source]
        b = graph.nodes[edge.target]
        x1, y1 = int(round(a.x)), int(round(a.y))
        x2, y2 = int(round(b.x)), int(round(b.y))
        # Bresenham's line algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        while True:
            if 0 <= x1 < width and 0 <= y1 < height:
                if grid[y1][x1] == " ":
                    grid[y1][x1] = "·"
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    # Draw nodes (over edges)
    for node in graph.nodes.values():
        x, y = int(round(node.x)), int(round(node.y))
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = "●" if node.degree > 0 else "○"

    return "\n".join("".join(row).rstrip() for row in grid)
