"""Obsidian vault reader — scans .md files, parses frontmatter, resolves wikilinks."""

from __future__ import annotations

import re
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


def _extract_title(path: Path, content: str) -> str:
    """Extract title from frontmatter, or fall back to first # heading, or filename."""
    try:
        post = frontmatter.loads(content)
        if post.get("title"):
            return str(post["title"])
    except Exception:
        pass

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()

    return path.stem


def _extract_tags(content: str) -> list[str]:
    """Extract tags from frontmatter."""
    try:
        post = frontmatter.loads(content)
        tags = post.get("tags", [])
        if isinstance(tags, list):
            return [str(t) for t in tags]
    except Exception:
        pass
    return []


def scan_vault(vault_path: Path, exclude_dirs: list[str] | None = None) -> list[Note]:
    """Scan an Obsidian vault directory for all .md files, returning Note objects."""
    exclude_dirs = exclude_dirs or []
    notes: list[Note] = []

    for md_file in vault_path.rglob("*.md"):
        parts = set(md_file.relative_to(vault_path).parts[:-1])
        if parts & set(exclude_dirs):
            continue

        content = md_file.read_text(encoding="utf-8")
        title = _extract_title(md_file, content)
        tags = _extract_tags(content)

        notes.append(Note(path=md_file, title=title, tags=tags, content=content))

    return notes


class VaultReader:
    """Reads and indexes an Obsidian vault."""

    def __init__(self, vault_path: Path, exclude_dirs: list[str] | None = None):
        self.vault_path = vault_path
        self.exclude_dirs = exclude_dirs or []
        self._notes: list[Note] = []
        self._by_slug: dict[str, Note] = {}
        self.refresh()

    def refresh(self) -> None:
        """Re-scan the vault and rebuild indexes."""
        self._notes = scan_vault(self.vault_path, self.exclude_dirs)
        self._by_slug = {}
        for note in self._notes:
            slug = note.title.lower().replace(" ", "-")
            self._by_slug[slug] = note
            self._by_slug[note.title.lower()] = note

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
