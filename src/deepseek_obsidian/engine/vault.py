"""Obsidian vault reader — scans .md files, parses frontmatter, resolves wikilinks."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass
class Note:
    path: Path
    title: str
    tags: list[str] = field(default_factory=list)
    content: str = ""

    def preview(self, max_chars: int = 500) -> str:
        if len(self.content) <= max_chars:
            return self.content
        return self.content[:max_chars - 3] + "..."

    def wikilinks(self) -> list[str]:
        return WIKILINK_PATTERN.findall(self.content)


def _parse_metadata(path: Path, content: str) -> tuple[str, list[str]]:
    """Parse frontmatter once, returning title and tags.

    Title fallback: first # heading, then filename stem.
    """
    tags: list[str] = []
    title = ""
    try:
        post = frontmatter.loads(content)
        if post.get("title"):
            title = str(post["title"])
        fm_tags = post.get("tags", [])
        if isinstance(fm_tags, list):
            tags = [str(t) for t in fm_tags]
    except Exception:
        pass

    if not title:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
    if not title:
        title = path.stem

    return title, tags


def scan_vault(vault_path: Path, exclude_dirs: list[str] | None = None) -> list[Note]:
    """Scan an Obsidian vault directory for all .md files, returning Note objects."""
    exclude_set = set(exclude_dirs or [])
    notes: list[Note] = []

    for dirpath_str, dirnames, filenames in os.walk(str(vault_path)):
        # Prune excluded directories before descending
        dirnames[:] = [d for d in dirnames if d not in exclude_set]

        dirpath = Path(dirpath_str)
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            md_file = dirpath / filename
            content = md_file.read_text(encoding="utf-8")
            title, tags = _parse_metadata(md_file, content)
            notes.append(Note(path=md_file, title=title, tags=tags, content=content))

    return notes


class VaultReader:
    """Reads and indexes an Obsidian vault."""

    def __init__(
        self,
        vault_path: Path,
        exclude_dirs: list[str] | None = None,
        on_change: Callable[[], None] | None = None,
    ):
        self.vault_path = vault_path
        self.exclude_dirs = exclude_dirs or []
        self._notes: list[Note] = []
        self._by_slug: dict[str, Note] = {}
        self._on_change = on_change
        self._watcher_task: asyncio.Task | None = None
        self.refresh()

    def refresh(self) -> None:
        """Re-scan the vault and rebuild indexes."""
        self._notes = scan_vault(self.vault_path, self.exclude_dirs)
        self._by_slug = {}
        for note in self._notes:
            slug = note.title.lower().replace(" ", "-")
            self._by_slug[slug] = note
            self._by_slug[note.title.lower()] = note

    async def start_watcher(self) -> None:
        """Watch vault for .md file changes and auto-refresh."""
        if self._watcher_task is not None:
            return

        from watchfiles import awatch

        async def _watch() -> None:
            async for _ in awatch(str(self.vault_path)):
                self.refresh()
                if self._on_change:
                    self._on_change()

        self._watcher_task = asyncio.create_task(_watch())

    def stop_watcher(self) -> None:
        """Stop the file watcher if running."""
        if self._watcher_task:
            self._watcher_task.cancel()
            self._watcher_task = None

    @property
    def notes(self) -> list[Note]:
        return self._notes

    def resolve_wikilink(self, link: str) -> Note | None:
        """Resolve a [[wikilink]] to a Note, if it exists in the vault."""
        slug = link.lower().strip()
        return self._by_slug.get(slug)

    def backlinks(self, target_title: str) -> list[Note]:
        """Find all notes that link to the given note title."""
        target = target_title.lower().strip()
        results: list[Note] = []
        for note in self._notes:
            links = [link.lower().strip() for link in note.wikilinks()]
            if target in links:
                results.append(note)
        return results

    def search_by_title(self, query: str) -> list[Note]:
        """Simple title-based search."""
        q = query.lower()
        return [n for n in self._notes if q in n.title.lower()]

    def search_full_text(self, query: str) -> list[Note]:
        """Full-text search across note content."""
        q = query.lower()
        results: list[tuple[int, Note]] = []
        for note in self._notes:
            score = 0
            if q in note.title.lower():
                score += 10
            score += note.content.lower().count(q)
            if score > 0:
                results.append((score, note))
        results.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in results]
