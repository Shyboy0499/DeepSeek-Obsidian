"""Obsidian vault reader — scans .md files, parses frontmatter, resolves wikilinks."""

from __future__ import annotations

import asyncio
import math
import os
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")

# Common English stopwords for better semantic matching
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "of",
    "to", "in", "on", "at", "by", "for", "with", "about", "is", "are",
    "was", "were", "be", "been", "being", "this", "that", "these",
    "those", "it", "its", "as", "from", "into", "than", "not", "no",
    "so", "do", "does", "did", "have", "has", "had", "i", "you", "he",
    "she", "we", "they", "them", "his", "her", "their", "my", "your",
}


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens, removing stopwords."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


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


def update_tags(note: Note, add: list[str] | None = None, remove: list[str] | None = None) -> None:
    """Add and/or remove frontmatter tags on a note, writing back to disk."""
    add = add or []
    remove = remove or []
    try:
        post = frontmatter.loads(note.content)
    except Exception:
        post = frontmatter.Post("")
    tags = post.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, list):
        tags = []
    tags = [str(t) for t in tags]
    for t in remove:
        if t in tags:
            tags.remove(t)
    for t in add:
        if t not in tags:
            tags.append(t)
    post["tags"] = tags
    note.path.write_text(frontmatter.dumps(post))
    note.content = note.path.read_text(encoding="utf-8")
    note.tags = tags


def scan_vault(
    vault_path: Path,
    exclude_dirs: list[str] | None = None,
    cache: dict[Path, tuple[float, Note]] | None = None,
) -> list[Note]:
    """Scan an Obsidian vault directory for all .md files, returning Note objects.

    If a `cache` dict (mapping path -> (mtime, Note)) is provided, unchanged files
    (same mtime) are reused from cache instead of being re-parsed. This makes
    re-scans cheap — only changed/new files are parsed.
    """
    exclude_set = set(exclude_dirs or [])
    notes: list[Note] = []
    cache = cache if cache is not None else {}
    new_cache: dict[Path, tuple[float, Note]] = {}

    for dirpath_str, dirnames, filenames in os.walk(str(vault_path)):
        # Prune excluded directories before descending
        dirnames[:] = [d for d in dirnames if d not in exclude_set]

        dirpath = Path(dirpath_str)
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            md_file = dirpath / filename
            try:
                mtime = md_file.stat().st_mtime
            except OSError:
                continue

            cached = cache.get(md_file)
            if cached is not None and cached[0] == mtime:
                note = cached[1]
            else:
                content = md_file.read_text(encoding="utf-8")
                title, tags = _parse_metadata(md_file, content)
                note = Note(path=md_file, title=title, tags=tags, content=content)
            notes.append(note)
            new_cache[md_file] = (mtime, note)

    # Drop entries for deleted files
    cache.clear()
    cache.update(new_cache)
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
        self._cache: dict[Path, tuple[float, Note]] = {}
        self.refresh()

    def refresh(self) -> None:
        """Re-scan the vault and rebuild indexes (incremental via mtime cache)."""
        self._notes = scan_vault(self.vault_path, self.exclude_dirs, self._cache)
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

    def search_semantic(self, query: str, limit: int | None = None) -> list[Note]:
        """Rank notes by TF-IDF cosine similarity to the query.

        Better than substring matching: finds notes that discuss a topic even
        when they don't contain the exact query words. Uses a lightweight
        bag-of-words model with term frequency and inverse document frequency.
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return self.search_full_text(query)

        # Document frequency: how many notes contain each term
        doc_freq: Counter = Counter()
        note_tokens: dict[str, list[str]] = {}
        for note in self._notes:
            tokens = _tokenize(note.content + " " + note.title)
            note_tokens[note.title] = tokens
            doc_freq.update(set(tokens))

        num_notes = max(len(self._notes), 1)

        def idf(term: str) -> float:
            return math.log((1 + num_notes) / (1 + doc_freq[term])) + 1.0

        # Build query vector
        q_vec: Counter = Counter(query_tokens)
        q_norm = math.sqrt(sum((idf(t) * c) ** 2 for t, c in q_vec.items()))

        scored: list[tuple[float, Note]] = []
        for note in self._notes:
            tokens = note_tokens[note.title]
            if not tokens:
                continue
            tf = Counter(tokens)
            # Cosine similarity between query and note term vectors
            dot = 0.0
            norm = 0.0
            for term, count in tf.items():
                w = idf(term) * count
                norm += w * w
                if term in q_vec:
                    dot += w * (idf(term) * q_vec[term])
            if norm == 0 or q_norm == 0:
                continue
            similarity = dot / (math.sqrt(norm) * q_norm)
            if similarity > 0:
                scored.append((similarity, note))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [n for _, n in scored]
        if limit:
            return results[:limit]
        return results
