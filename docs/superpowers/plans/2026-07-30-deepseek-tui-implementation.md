# DeepSeek-Obsidian Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-native note-taking and research TUI with deep Obsidian vault integration, using Python + Textual.

**Architecture:** Three-layer design — Core Engine (pure Python: vault reader, AI client, context builder, permissions), TUI Layer (Textual app with chat-primary layout, sidebar, input bar, header), and Distribution (pip + Homebrew). Each layer is independently testable. The engine has zero TUI dependency.

**Tech Stack:** Python 3.12+, Textual, httpx, python-frontmatter, tomli, pytest, pytest-asyncio

---

### Task 1: Project Scaffold and Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `src/deepseek_obsidian/__init__.py`
- Create: `src/deepseek_obsidian/__main__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Write pyproject.toml with all dependencies**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "deepseek-obsidian"
version = "0.1.0"
description = "AI-native note-taking and research assistant for the terminal with Obsidian integration"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.12"
dependencies = [
    "textual>=1.0.0",
    "httpx>=0.27.0",
    "python-frontmatter>=1.1.0",
    "tomli>=2.0.0; python_version < '3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0",
    "ruff>=0.5.0",
    "mypy>=1.10",
]

[project.scripts]
deepseek-obsidian = "deepseek_obsidian.app:main"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = true
```

- [ ] **Step 2: Write `__init__.py`**

```python
"""DeepSeek-Obsidian: AI-native note-taking and research assistant for the terminal."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Write `__main__.py`**

```python
"""Allow running as `python -m deepseek_obsidian`."""

from deepseek_obsidian.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write `tests/__init__.py`** (empty file)

- [ ] **Step 5: Write `.gitignore`**

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.coverage
htmlcov/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.venv/
venv/
.env
```

- [ ] **Step 6: Create virtualenv, install, and verify CLI entrypoint exists**

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]" && deepseek-obsidian --help 2>&1 || true
```
Expected: fails with ModuleNotFoundError for `deepseek_obsidian.app` (app.py not written yet — expected at this stage)

- [ ] **Step 7: Verify test infrastructure works**

```bash
python -m pytest -v
```
Expected: "no tests ran" (or 0 collected) — pytest itself works

- [ ] **Step 8: Commit and push**

```bash
git add pyproject.toml src/deepseek_obsidian/__init__.py src/deepseek_obsidian/__main__.py tests/__init__.py .gitignore
git commit -m "chore: scaffold project with pyproject.toml and dev tooling"
git push origin main
```

---

### Task 2: Config System

**Files:**
- Create: `src/deepseek_obsidian/config/__init__.py`
- Create: `src/deepseek_obsidian/config/defaults.py`
- Create: `src/deepseek_obsidian/config/loader.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for config loading and defaults."""

import os
import tempfile
from pathlib import Path
from deepseek_obsidian.config.loader import load_config, Config
from deepseek_obsidian.config.defaults import DEFAULTS


class TestDefaults:
    def test_default_vault_path_is_none(self):
        assert DEFAULTS["vault"]["path"] is None

    def test_default_provider_is_deepseek(self):
        assert DEFAULTS["model"]["provider"] == "deepseek"
        assert DEFAULTS["model"]["model"] == "deepseek-chat"

    def test_default_permission_is_ask(self):
        assert DEFAULTS["tui"]["permission_default"] == "ask"

    def test_default_max_notes_is_10(self):
        assert DEFAULTS["context"]["max_notes"] == 10


class TestLoadConfig:
    def test_loads_defaults_when_no_config_file(self):
        config = load_config(config_path=Path("/nonexistent/path/config.toml"))
        assert config.vault_path is None
        assert config.provider == "deepseek"
        assert config.model == "deepseek-chat"

    def test_merges_config_file_over_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[vault]
path = "/home/user/notes"

[model]
provider = "anthropic"
model = "claude-sonnet-4-6"

[tui]
permission_default = "full"
""")
            f.flush()
            config = load_config(config_path=Path(f.name))
        os.unlink(f.name)

        assert config.vault_path == Path("/home/user/notes")
        assert config.provider == "anthropic"
        assert config.model == "claude-sonnet-4-6"
        assert config.permission_default == "full"

    def test_reads_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
        config = load_config()
        assert config.api_key == "sk-test-123"

    def test_respects_exclude_dirs_from_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[vault]
exclude_dirs = [".git", "_templates"]
""")
            f.flush()
            config = load_config(config_path=Path(f.name))
        os.unlink(f.name)

        assert ".git" in config.exclude_dirs
        assert "_templates" in config.exclude_dirs

    def test_expands_tilde_in_path(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[vault]
path = "~/Documents/Obsidian/Vault"
""")
            f.flush()
            config = load_config(config_path=Path(f.name))
        os.unlink(f.name)

        assert config.vault_path == Path.home() / "Documents/Obsidian/Vault"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with ModuleNotFoundError (no config module yet)

- [ ] **Step 3: Write `defaults.py`**

```python
"""Default configuration values."""

from typing import Any

DEFAULTS: dict[str, dict[str, Any]] = {
    "vault": {
        "path": None,
        "exclude_dirs": [".git", "_templates", ".trash"],
    },
    "model": {
        "provider": "deepseek",
        "model": "deepseek-chat",
    },
    "context": {
        "max_notes": 10,
        "note_preview_chars": 500,
        "full_text_search": True,
        "incremental_index": True,
    },
    "tui": {
        "theme": "dracula",
        "permission_default": "ask",
        "sidebar_width": 35,
    },
}
```

- [ ] **Step 4: Write `loader.py`**

```python
"""Configuration loader — reads TOML config and environment variables."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepseek_obsidian.config.defaults import DEFAULTS

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


CONFIG_DIR = Path.home() / ".config" / "deepseek-obsidian"
CONFIG_PATH = CONFIG_DIR / "config.toml"


@dataclass
class Config:
    vault_path: Path | None
    exclude_dirs: list[str]
    provider: str
    model: str
    max_notes: int
    note_preview_chars: int
    full_text_search: bool
    incremental_index: bool
    theme: str
    permission_default: str
    sidebar_width: int
    api_key: str | None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override dict into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_api_key(config: dict[str, Any]) -> str | None:
    """Read API key from environment based on provider."""
    provider = config["model"]["provider"]
    env_var_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "ollama": None,  # local — no key needed
    }
    var_name = env_var_map.get(provider)
    if var_name is None:
        return None
    return os.environ.get(var_name)


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration, merging defaults with config file and env vars."""
    config_path = config_path or CONFIG_PATH
    cfg: dict[str, Any] = DEFAULTS

    if config_path.exists():
        file_data = tomllib.loads(config_path.read_text())
        cfg = _deep_merge(cfg, file_data)

    vault_path_raw: str | None = cfg["vault"]["path"]
    vault_path = Path(vault_path_raw).expanduser() if vault_path_raw else None

    return Config(
        vault_path=vault_path,
        exclude_dirs=cfg["vault"]["exclude_dirs"],
        provider=cfg["model"]["provider"],
        model=cfg["model"]["model"],
        max_notes=cfg["context"]["max_notes"],
        note_preview_chars=cfg["context"]["note_preview_chars"],
        full_text_search=cfg["context"]["full_text_search"],
        incremental_index=cfg["context"]["incremental_index"],
        theme=cfg["tui"]["theme"],
        permission_default=cfg["tui"]["permission_default"],
        sidebar_width=cfg["tui"]["sidebar_width"],
        api_key=_read_api_key(cfg),
    )
```

- [ ] **Step 5: Write `config/__init__.py`**

```python
"""Configuration subsystem."""

from deepseek_obsidian.config.loader import Config, load_config

__all__ = ["Config", "load_config"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: all 6 tests PASS

- [ ] **Step 7: Commit and push**

```bash
git add src/deepseek_obsidian/config/ tests/test_config.py
git commit -m "feat: add config system with TOML loading and env var support"
git push origin main
```

---

### Task 3: Vault Reader

**Files:**
- Create: `src/deepseek_obsidian/engine/__init__.py`
- Create: `src/deepseek_obsidian/engine/vault.py`
- Create: `tests/conftest.py`
- Create: `tests/test_vault.py`

- [ ] **Step 1: Write `tests/conftest.py` with temp vault fixture**

```python
"""Shared test fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_vault() -> Path:
    """Create a temporary Obsidian-like vault with .md files and .obsidian/ config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        (vault / ".obsidian").mkdir()

        # Note with frontmatter
        (vault / "note1.md").write_text("""---
title: Machine Learning Basics
tags: [ml, beginner]
---

# Machine Learning Basics

This is about [[neural networks]] and [[deep learning]].

Some content here.
""")

        # Note without frontmatter
        (vault / "note2.md").write_text("""# Neural Networks

Neural networks are the foundation of [[deep learning]].

Backpropagation is key to training.
""")

        # Note in a subdirectory
        subdir = vault / "topics"
        subdir.mkdir()
        (subdir / "deep-learning.md").write_text("""---
title: Deep Learning
tags: [ml, advanced]
---

# Deep Learning

Building on [[machine learning basics]] and [[neural networks]].
""")

        # A non-markdown file (should be ignored)
        (vault / "image.png").write_text("fake image")

        # An excluded directory
        excluded = vault / "_templates"
        excluded.mkdir()
        (excluded / "template.md").write_text("# Template Note")

        yield vault
```

- [ ] **Step 2: Write failing tests for vault reader**

```python
"""Tests for vault reader."""

from pathlib import Path
from deepseek_obsidian.engine.vault import VaultReader, Note, scan_vault


class TestNote:
    def test_creates_from_filepath(self):
        note = Note(
            path=Path("/vault/note1.md"),
            title="Test Note",
            tags=["ml"],
            content="Full content here",
        )
        assert note.path == Path("/vault/note1.md")
        assert note.title == "Test Note"
        assert note.tags == ["ml"]
        assert note.content == "Full content here"

    def test_preview_truncates_content(self):
        note = Note(
            path=Path("/vault/n.md"),
            title="Note",
            tags=[],
            content="x" * 1000,
        )
        preview = note.preview(max_chars=200)
        assert len(preview) <= 200
        assert preview.endswith("...")

    def test_wikilinks_extracts_links(self):
        note = Note(
            path=Path("/vault/n.md"),
            title="Test",
            tags=[],
            content="See [[alpha]] and [[beta]] for more.",
        )
        assert note.wikilinks() == ["alpha", "beta"]


class TestScanVault:
    def test_finds_all_markdown_files(self, temp_vault):
        notes = scan_vault(temp_vault)
        paths = {n.path.name for n in notes}
        assert "note1.md" in paths
        assert "note2.md" in paths
        assert "deep-learning.md" in paths
        assert "image.png" not in paths  # non-markdown ignored

    def test_excludes_specified_directories(self, temp_vault):
        notes = scan_vault(temp_vault, exclude_dirs=["_templates"])
        paths = {n.path.name for n in notes}
        assert "template.md" not in paths

    def test_parses_frontmatter_title(self, temp_vault):
        notes = scan_vault(temp_vault)
        note1 = next(n for n in notes if n.path.name == "note1.md")
        assert note1.title == "Machine Learning Basics"

    def test_parses_frontmatter_tags(self, temp_vault):
        notes = scan_vault(temp_vault)
        note1 = next(n for n in notes if n.path.name == "note1.md")
        assert "ml" in note1.tags
        assert "beginner" in note1.tags

    def test_falls_back_to_first_heading_when_no_frontmatter_title(self, temp_vault):
        notes = scan_vault(temp_vault)
        note2 = next(n for n in notes if n.path.name == "note2.md")
        assert note2.title == "Neural Networks"

    def test_finds_notes_in_subdirectories(self, temp_vault):
        notes = scan_vault(temp_vault)
        dl = next(n for n in notes if n.path.name == "deep-learning.md")
        assert dl.title == "Deep Learning"

    def test_reverse_lookup_finds_backlinks(self, temp_vault):
        vault = VaultReader(temp_vault)
        backlinks = vault.backlinks("neural networks")
        # note1 and deep-learning both link to "neural networks"
        titles = {n.title for n in backlinks}
        assert "Machine Learning Basics" in titles
        assert "Deep Learning" in titles

    def test_resolve_wikilink_finds_note_by_slug(self, temp_vault):
        vault = VaultReader(temp_vault)
        note = vault.resolve_wikilink("neural networks")
        assert note is not None
        assert note.title == "Neural Networks"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_vault.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 4: Write `engine/__init__.py`**

```python
"""Core engine — no TUI dependency."""
```

- [ ] **Step 5: Write `engine/vault.py`**

```python
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
        return self.content[:max_chars] + "..."

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
        # Skip excluded directories
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
            # Also index by exact title (lowered)
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
            links = [l.lower().strip() for l in note.wikilinks()]
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
        results: list[Note] = []
        for note in self._notes:
            score = 0
            if q in note.title.lower():
                score += 10
            score += note.content.lower().count(q)
            if score > 0:
                results.append((score, note))
        results.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in results]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_vault.py -v`
Expected: all 10 tests PASS

- [ ] **Step 7: Commit and push**

```bash
git add src/deepseek_obsidian/engine/__init__.py src/deepseek_obsidian/engine/vault.py tests/conftest.py tests/test_vault.py
git commit -m "feat: add vault reader with frontmatter parsing and wikilink resolution"
git push origin main
```

---

### Task 4: Permission Model and Audit Trail

**Files:**
- Create: `src/deepseek_obsidian/engine/permissions.py`
- Create: `tests/test_permissions.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for permission model and audit trail."""

import json
import tempfile
from pathlib import Path

import pytest
from deepseek_obsidian.engine.permissions import (
    AuditEntry,
    AuditTrail,
    PermissionLevel,
    Permissions,
)


class TestPermissionLevel:
    def test_ask_allows_read_only(self):
        perm = PermissionLevel.ASK
        assert perm.allows_read() is True
        assert perm.allows_propose() is False
        assert perm.allows_write() is False

    def test_auto_review_allows_read_and_propose(self):
        perm = PermissionLevel.AUTO_REVIEW
        assert perm.allows_read() is True
        assert perm.allows_propose() is True
        assert perm.allows_write() is False

    def test_full_access_allows_everything(self):
        perm = PermissionLevel.FULL_ACCESS
        assert perm.allows_read() is True
        assert perm.allows_propose() is True
        assert perm.allows_write() is True

    def test_cycle_next_rotates(self):
        assert PermissionLevel.ASK.next() == PermissionLevel.AUTO_REVIEW
        assert PermissionLevel.AUTO_REVIEW.next() == PermissionLevel.FULL_ACCESS
        assert PermissionLevel.FULL_ACCESS.next() == PermissionLevel.ASK

    def test_from_string(self):
        assert PermissionLevel.from_string("ask") == PermissionLevel.ASK
        assert PermissionLevel.from_string("review") == PermissionLevel.AUTO_REVIEW
        assert PermissionLevel.from_string("full") == PermissionLevel.FULL_ACCESS
        with pytest.raises(ValueError):
            PermissionLevel.from_string("invalid")


class TestPermissions:
    def test_default_is_ask(self):
        p = Permissions()
        assert p.level == PermissionLevel.ASK

    def test_cycle_changes_level(self):
        p = Permissions()
        p.cycle()
        assert p.level == PermissionLevel.AUTO_REVIEW
        p.cycle()
        assert p.level == PermissionLevel.FULL_ACCESS
        p.cycle()
        assert p.level == PermissionLevel.ASK

    def test_set_level(self):
        p = Permissions()
        p.set_level(PermissionLevel.FULL_ACCESS)
        assert p.level == PermissionLevel.FULL_ACCESS

    def test_ask_rejects_writes(self):
        p = Permissions()
        assert p.can_write() is False

    def test_full_access_allows_write(self):
        p = Permissions()
        p.set_level(PermissionLevel.FULL_ACCESS)
        assert p.can_write() is True


class TestAuditTrail:
    def test_records_entries(self):
        trail = AuditTrail()
        trail.record("write", "note1.md", "added [[link]] to content")
        assert len(trail.entries) == 1
        assert trail.entries[0].action == "write"
        assert trail.entries[0].target == "note1.md"

    def test_last_entry_returns_most_recent(self):
        trail = AuditTrail()
        trail.record("read", "note1.md", "")
        trail.record("write", "note2.md", "created note")
        assert trail.last_entry is not None
        assert trail.last_entry.action == "write"

    def test_save_and_load(self):
        trail = AuditTrail()
        trail.record("write", "note1.md", "edit")
        trail.record("write", "note2.md", "create")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            trail.save(Path(f.name))
            path = f.name

        loaded = AuditTrail.load(Path(path))
        Path(path).unlink()

        assert len(loaded.entries) == 2
        assert loaded.entries[0].target == "note1.md"
        assert loaded.entries[1].target == "note2.md"

    def test_can_undo_last_write(self):
        trail = AuditTrail()
        trail.record("write", "note1.md", "old content")
        entry = trail.pop_last_write()
        assert entry is not None
        assert entry.target == "note1.md"
        assert entry.previous_content == "old content"
        assert len(trail.entries) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_permissions.py -v`
Expected: FAIL

- [ ] **Step 3: Write `engine/permissions.py`**

```python
"""Progressive permission model for note operations and audit trail."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PermissionLevel(Enum):
    ASK = "ask"
    AUTO_REVIEW = "review"
    FULL_ACCESS = "full"

    def allows_read(self) -> bool:
        return True  # Always allowed

    def allows_propose(self) -> bool:
        return self in (PermissionLevel.AUTO_REVIEW, PermissionLevel.FULL_ACCESS)

    def allows_write(self) -> bool:
        return self == PermissionLevel.FULL_ACCESS

    def next(self) -> PermissionLevel:
        levels = list(PermissionLevel)
        idx = levels.index(self)
        return levels[(idx + 1) % len(levels)]

    @classmethod
    def from_string(cls, s: str) -> PermissionLevel:
        mapping = {
            "ask": cls.ASK,
            "review": cls.AUTO_REVIEW,
            "full": cls.FULL_ACCESS,
        }
        if s.lower() not in mapping:
            raise ValueError(f"Unknown permission level: {s}")
        return mapping[s.lower()]


@dataclass
class AuditEntry:
    timestamp: float = field(default_factory=time.time)
    action: str = ""  # "read", "propose", "write"
    target: str = ""  # filename or note title
    detail: str = ""  # description of the change
    previous_content: str = ""  # for undo support


class AuditTrail:
    """Append-only log of all write operations for review and undo."""

    def __init__(self):
        self._entries: list[AuditEntry] = []

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    @property
    def last_entry(self) -> AuditEntry | None:
        return self._entries[-1] if self._entries else None

    def record(self, action: str, target: str, detail: str, previous_content: str = "") -> None:
        self._entries.append(AuditEntry(
            action=action,
            target=target,
            detail=detail,
            previous_content=previous_content,
        ))

    def pop_last_write(self) -> AuditEntry | None:
        """Find the most recent write and remove it from the trail."""
        for i in range(len(self._entries) - 1, -1, -1):
            if self._entries[i].action == "write":
                return self._entries.pop(i)
        return None

    def save(self, path: Path) -> None:
        data = [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "target": e.target,
                "detail": e.detail,
                "previous_content": e.previous_content,
            }
            for e in self._entries
        ]
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> AuditTrail:
        trail = cls()
        if path.exists():
            data = json.loads(path.read_text())
            for entry in data:
                trail._entries.append(AuditEntry(
                    timestamp=entry["timestamp"],
                    action=entry["action"],
                    target=entry["target"],
                    detail=entry["detail"],
                    previous_content=entry.get("previous_content", ""),
                ))
        return trail


class Permissions:
    """Manages current permission level for the session."""

    def __init__(self, level: PermissionLevel = PermissionLevel.ASK):
        self.level = level
        self._audit_trail = AuditTrail()

    @property
    def audit_trail(self) -> AuditTrail:
        return self._audit_trail

    def cycle(self) -> PermissionLevel:
        self.level = self.level.next()
        return self.level

    def set_level(self, level: PermissionLevel) -> None:
        self.level = level

    def can_propose(self) -> bool:
        return self.level.allows_propose()

    def can_write(self) -> bool:
        return self.level.allows_write()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_permissions.py -v`
Expected: all 11 tests PASS

- [ ] **Step 5: Commit and push**

```bash
git add src/deepseek_obsidian/engine/permissions.py tests/test_permissions.py
git commit -m "feat: add permission model with three-level posture and audit trail"
git push origin main
```

---

### Task 5: AI Client (Multi-Provider with Streaming)

**Files:**
- Create: `src/deepseek_obsidian/engine/ai_client.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for multi-provider AI client."""

import pytest
from deepseek_obsidian.engine.ai_client import (
    AIProvider,
    AIClient,
    Message,
    StreamChunk,
    create_client,
)


class TestMessage:
    def test_user_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self):
        msg = Message(role="system", content="You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."

    def test_to_dict(self):
        msg = Message(role="user", content="Hi")
        assert msg.to_dict() == {"role": "user", "content": "Hi"}


class TestStreamChunk:
    def test_creates_with_content(self):
        chunk = StreamChunk(content="Hello")
        assert chunk.content == "Hello"
        assert chunk.is_done is False

    def test_done_chunk(self):
        chunk = StreamChunk(content="", is_done=True)
        assert chunk.is_done is True


class TestAIProvider:
    def test_all_providers_have_base_url(self):
        for provider in AIProvider:
            assert provider.base_url is not None

    def test_default_model_for_each_provider(self):
        models = {
            AIProvider.DEEPSEEK: "deepseek-chat",
            AIProvider.ANTHROPIC: "claude-sonnet-4-6",
            AIProvider.OPENAI: "gpt-4o",
            AIProvider.OLLAMA: "llama3",
        }
        for provider, expected_model in models.items():
            assert provider.default_model == expected_model


class TestCreateClient:
    def test_creates_deepseek_client_with_key(self):
        client = create_client("deepseek", "deepseek-chat", api_key="sk-test")
        assert client.provider == AIProvider.DEEPSEEK

    def test_creates_ollama_client_without_key(self):
        client = create_client("ollama", "llama3")
        assert client.provider == AIProvider.OLLAMA
        assert client.api_key is None

    def test_raises_for_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_client("unknown", "model")


class TestAIClient:
    def test_builds_request_headers(self):
        client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat", api_key="sk-abc")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer sk-abc"
        assert headers["Content-Type"] == "application/json"

    def test_builds_request_body(self):
        client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat")
        messages = [
            Message(role="system", content="You are a note assistant."),
            Message(role="user", content="Summarize my notes."),
        ]
        body = client._build_body(messages)
        assert body["model"] == "deepseek-chat"
        assert body["stream"] is True
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"

    def test_system_prompt_includes_note_context(self, temp_vault):
        """Integration-ish: system prompt builder uses vault context."""
        from deepseek_obsidian.engine.vault import VaultReader

        vault = VaultReader(temp_vault)
        note = vault.resolve_wikilink("machine learning basics")

        client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat")
        prompt = client.build_system_prompt(
            context_notes=[note] if note else [],
            permission_level="ask",
        )
        assert "Obsidian vault" in prompt
        assert "Machine Learning Basics" in prompt or "note-taking" in prompt.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai_client.py -v`
Expected: FAIL

- [ ] **Step 3: Write `engine/ai_client.py`**

```python
"""Multi-provider AI client with streaming support."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator

import httpx

from deepseek_obsidian.engine.vault import Note


class AIProvider(Enum):
    DEEPSEEK = ("deepseek", "https://api.deepseek.com/v1", "deepseek-chat")
    ANTHROPIC = ("anthropic", "https://api.anthropic.com/v1", "claude-sonnet-4-6")
    OPENAI = ("openai", "https://api.openai.com/v1", "gpt-4o")
    OLLAMA = ("ollama", "http://localhost:11434/v1", "llama3")

    def __new__(cls, value: str, base_url: str, default_model: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.base_url = base_url
        obj.default_model = default_model
        return obj

    @classmethod
    def from_string(cls, s: str) -> AIProvider:
        for provider in cls:
            if provider.value == s.lower():
                return provider
        raise ValueError(f"Unknown provider: {s}")


@dataclass
class Message:
    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class StreamChunk:
    content: str
    is_done: bool = False


class AIClient:
    """Handles communication with AI providers using OpenAI-compatible API."""

    def __init__(self, provider: AIProvider, model: str, api_key: str | None = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_body(self, messages: list[Message]) -> dict:
        return {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }

    def build_system_prompt(
        self,
        context_notes: list[Note],
        permission_level: str = "ask",
    ) -> Message:
        """Build a system prompt that includes vault context and permission rules."""

        lines = [
            "You are an AI note-taking and research assistant.",
            f"You have access to the user's Obsidian vault.",
            f"Current permission level: {permission_level}.",
            "",
        ]

        if permission_level == "ask":
            lines.append(
                "You may READ notes, SEARCH the vault, and SUGGEST links or edits. "
                "You may NOT write to the vault. When you propose an edit or new note, "
                "present it as a suggestion for the user to approve."
            )
        elif permission_level == "review":
            lines.append(
                "You may READ notes, SEARCH the vault, PROPOSE edits, and DRAFT new notes. "
                "Proposed changes will be reviewed by the user before being written."
            )
        elif permission_level == "full":
            lines.append(
                "You have FULL ACCESS. You may read, edit, and create notes. "
                "All writes are logged to an audit trail."
            )

        if context_notes:
            lines.append("")
            lines.append("## Relevant Notes from Vault")
            for note in context_notes:
                rel_path = note.path.name  # simplified for context window
                lines.append(f"### {note.title} (`{rel_path}`)")
                if note.tags:
                    lines.append(f"Tags: {', '.join(note.tags)}")
                lines.append(note.preview(max_chars=500))
                lines.append("")

        return Message(role="system", content="\n".join(lines))

    async def stream(
        self,
        messages: list[Message],
    ) -> AsyncIterator[StreamChunk]:
        """Send messages to the AI provider and stream chunks back."""
        body = self._build_body(messages)

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.provider.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            yield StreamChunk(content="", is_done=True)
                            return
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        yield StreamChunk(content="", is_done=True)


def create_client(provider: str, model: str, api_key: str | None = None) -> AIClient:
    """Factory function to create an AI client for a given provider."""
    prov = AIProvider.from_string(provider)
    return AIClient(prov, model, api_key)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai_client.py -v`
Expected: all tests PASS (note: the streaming test is a unit test, no live API call)

- [ ] **Step 5: Commit and push**

```bash
git add src/deepseek_obsidian/engine/ai_client.py tests/test_ai_client.py
git commit -m "feat: add multi-provider AI client with streaming support"
git push origin main
```

---

### Task 6: Context Builder

**Files:**
- Create: `src/deepseek_obsidian/engine/context.py`
- Create: `tests/test_context.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for context builder."""

from deepseek_obsidian.engine.context import ContextBuilder, ChatHistory
from deepseek_obsidian.engine.ai_client import Message
from deepseek_obsidian.engine.vault import VaultReader


class TestChatHistory:
    def test_adds_messages(self):
        history = ChatHistory(max_messages=10)
        history.add(Message(role="user", content="Hello"))
        history.add(Message(role="assistant", content="Hi there"))
        assert len(history.messages) == 2

    def test_trims_oldest_when_over_limit(self):
        history = ChatHistory(max_messages=3)
        for i in range(5):
            history.add(Message(role="user", content=str(i)))
        assert len(history.messages) == 3
        assert history.messages[0].content == "2"
        assert history.messages[-1].content == "4"

    def test_clear_removes_all(self):
        history = ChatHistory()
        history.add(Message(role="user", content="Hi"))
        history.clear()
        assert len(history.messages) == 0


class TestContextBuilder:
    def test_builds_context_from_query(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=5)

        messages = builder.build("machine learning")
        # Should have system message + user message
        assert len(messages) >= 2
        assert messages[0].role == "system"
        assert messages[-1].role == "user"
        assert messages[-1].content == "machine learning"

    def test_includes_wikilinked_note_when_mentioned(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=5)

        messages = builder.build("tell me about [[Neural Networks]]")
        system = messages[0].content
        assert "Neural Networks" in system

    def test_limits_context_notes_to_max(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=1)

        messages = builder.build("notes")
        system = messages[0].content
        # Count "### " headers in system prompt (one per note)
        note_headers = system.count("### ")
        # 1 note header + permission header — we count just the note ones
        assert note_headers <= 1

    def test_includes_chat_history(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=5)
        builder.history.add(Message(role="user", content="What is ML?"))
        builder.history.add(Message(role="assistant", content="ML is..."))

        messages = builder.build("tell me more")
        # Should have: system + user (history) + assistant (history) + user (new)
        assert len(messages) >= 3

    def test_vault_query_falls_back_to_all_notes_on_empty(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=5)

        messages = builder.build("xyznonexistent123")
        # Should still have a system prompt with the vault context
        assert len(messages) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_context.py -v`
Expected: FAIL

- [ ] **Step 3: Write `engine/context.py`**

```python
"""Context builder — searches vault and assembles prompts with note context."""

from __future__ import annotations

import re

from deepseek_obsidian.engine.ai_client import Message
from deepseek_obsidian.engine.vault import Note, VaultReader

WIKILINK_IN_QUERY = re.compile(r"\[\[([^\]]+)\]\]")


class ChatHistory:
    """Ring-buffer for chat messages."""

    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._messages: list[Message] = []

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    def add(self, message: Message) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def clear(self) -> None:
        self._messages.clear()


class ContextBuilder:
    """Builds AI prompts by searching the vault and assembling context."""

    def __init__(self, vault: VaultReader, max_notes: int = 10):
        self.vault = vault
        self.max_notes = max_notes
        self.history = ChatHistory()

    def _extract_wikilinks(self, query: str) -> list[Note]:
        """Find notes explicitly referenced via [[wikilinks]] in the query."""
        links = WIKILINK_IN_QUERY.findall(query)
        notes: list[Note] = []
        for link in links:
            note = self.vault.resolve_wikilink(link)
            if note:
                notes.append(note)
        return notes

    def _search_vault(self, query: str) -> list[Note]:
        """Quick pass: title search. Falls back to full-text if config allows."""
        results = self.vault.search_by_title(query)
        if not results:
            results = self.vault.search_full_text(query)
        return results[:self.max_notes]

    def build(
        self,
        query: str,
        permission_level: str = "ask",
        system_prompt_builder=None,
    ) -> list[Message]:
        """Build the full message list for an AI request.

        Args:
            query: The user's message.
            permission_level: Current permission posture.
            system_prompt_builder: Optional callable to build system prompt.
                                   Takes (context_notes, permission_level) -> Message.
        """
        from deepseek_obsidian.engine.ai_client import AIClient, AIProvider

        # Gather context notes
        linked_notes = self._extract_wikilinks(query)
        searched_notes = self._search_vault(query)

        # Merge: linked notes first, then searched, deduplicate by path
        seen = {n.path for n in linked_notes}
        context_notes = list(linked_notes)
        for note in searched_notes:
            if note.path not in seen:
                context_notes.append(note)
                seen.add(note.path)
        context_notes = context_notes[:self.max_notes]

        # Build system prompt
        if system_prompt_builder:
            system_msg = system_prompt_builder(context_notes, permission_level)
        else:
            client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat")
            system_msg = client.build_system_prompt(context_notes, permission_level)

        # Assemble full message list
        messages: list[Message] = [system_msg]
        messages.extend(self.history.messages)
        messages.append(Message(role="user", content=query))

        return messages, context_notes
```

Wait, the `build` method returns a tuple but I didn't annotate that. Let me fix the return type.

Actually, let me correct the return type — it should be `tuple[list[Message], list[Note]]`:

```python
    def build(
        self,
        query: str,
        permission_level: str = "ask",
        system_prompt_builder=None,
    ) -> tuple[list[Message], list[Note]]:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_context.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit and push**

```bash
git add src/deepseek_obsidian/engine/context.py tests/test_context.py
git commit -m "feat: add context builder with vault search and chat history"
git push origin main
```

---

### Task 7: TUI App Scaffold and Main Screen Layout

**Files:**
- Create: `src/deepseek_obsidian/app.py`
- Create: `src/deepseek_obsidian/tui/__init__.py`
- Create: `src/deepseek_obsidian/tui/screen.py`
- Create: `src/deepseek_obsidian/tui/widgets/__init__.py`

- [ ] **Step 1: Write `app.py` entry point**

```python
"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App


def main() -> None:
    """Launch the DeepSeek-Obsidian application."""
    from deepseek_obsidian.tui.screen import MainScreen

    class DeepSeekTuiApp(App):
        CSS_PATH = None  # Will be set when we have CSS

        def on_mount(self) -> None:
            self.push_screen(MainScreen())

    app = DeepSeekTuiApp()
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `tui/screen.py` main layout**

```python
"""Main TUI screen with chat-primary layout."""

from textual.screen import Screen
from textual.widgets import Static


class MainScreen(Screen):
    """Primary screen: chat on the left, sidebar on the right, input at bottom."""

    def compose(self):
        yield Static("DeepSeek-Obsidian — Loading...")

    def on_mount(self) -> None:
        self.title = "DeepSeek-Obsidian"
```

- [ ] **Step 3: Write empty `__init__.py` files**

```python
"""TUI layer — Textual widgets and screens."""
```

```python
"""TUI widgets."""
```

- [ ] **Step 4: Verify app launches (empty screen, exits cleanly)**

```bash
timeout 3 python -m deepseek_obsidian 2>&1 || true
```
Expected: Textual app launches then exits after timeout (no crash)

- [ ] **Step 5: Commit and push**

```bash
git add src/deepseek_obsidian/app.py src/deepseek_obsidian/tui/
git commit -m "feat: add TUI app scaffold and main screen"
git push origin main
```

---

### Task 8: Chat Widget (Streaming Markdown)

**Files:**
- Create: `src/deepseek_obsidian/tui/widgets/chat.py`

- [ ] **Step 1: Write the chat widget**

```python
"""Chat view widget — displays streaming AI responses with markdown rendering."""

from textual.containers import VerticalScroll
from textual.widgets import Static, Markdown


class ChatMessage(Static):
    """A single message bubble in the chat."""

    def __init__(self, role: str, content: str = ""):
        super().__init__("")
        self.role = role  # "user", "assistant", "system"
        self.content = content

    def on_mount(self) -> None:
        self._render()

    def _render(self) -> None:
        if self.role == "user":
            prefix = "🧑 You"
        elif self.role == "assistant":
            prefix = "🤖 Assistant"
        else:
            prefix = "⚙️ System"

        self.update(f"[bold]{prefix}[/bold]\n\n{self.content}")

    def append_chunk(self, chunk: str) -> None:
        """Stream a chunk of content to this message."""
        self.content += chunk
        self._render()


class ChatView(VerticalScroll):
    """Scrollable chat view that holds ChatMessage widgets."""

    def __init__(self):
        super().__init__()
        self._current_assistant_message: ChatMessage | None = None

    def add_user_message(self, content: str) -> None:
        msg = ChatMessage(role="user", content=content)
        self.mount(msg)
        self.scroll_end()

    def start_assistant_message(self) -> None:
        msg = ChatMessage(role="assistant", content="")
        self._current_assistant_message = msg
        self.mount(msg)

    def stream_chunk(self, chunk: str) -> None:
        if self._current_assistant_message:
            self._current_assistant_message.append_chunk(chunk)
            self.scroll_end()

    def finish_assistant_message(self) -> None:
        self._current_assistant_message = None

    def clear_chat(self) -> None:
        self.remove_children()
        self._current_assistant_message = None
```

- [ ] **Step 2: Verify chat widget works in isolation**

```bash
python -c "
from deepseek_obsidian.tui.widgets.chat import ChatView, ChatMessage
# Verify classes are importable and instantiable
cv = ChatView()
msg = ChatMessage('user', 'test')
msg.append_chunk(' more')
assert 'more' in msg.content
print('Chat widget tests passed')
"
```

- [ ] **Step 3: Commit and push**

```bash
git add src/deepseek_obsidian/tui/widgets/chat.py
git commit -m "feat: add chat widget with streaming markdown support"
git push origin main
```

---

### Task 9: Sidebar Widget (Notes + Search)

**Files:**
- Create: `src/deepseek_obsidian/tui/widgets/sidebar.py`

- [ ] **Step 1: Write the sidebar widget**

```python
"""Sidebar widget — referenced notes panel and search results."""

from textual.containers import Vertical, Container
from textual.widgets import Static, Input, ListView, ListItem


class ReferencedNotesPanel(Vertical):
    """Shows which notes the AI referenced in its response."""

    def __init__(self):
        super().__init__()
        self._notes: list[tuple[str, str]] = []  # (title, path)

    def compose(self):
        yield Static("[bold]📄 Referenced Notes[/bold]", classes="panel-title")
        yield ListView(id="notes-list")

    def set_notes(self, notes: list[tuple[str, str]]) -> None:
        """Update the list of referenced notes.

        Args:
            notes: List of (title, path) tuples.
        """
        self._notes = notes
        list_view = self.query_one("#notes-list", ListView)
        list_view.clear()
        for title, path in notes:
            list_view.append(ListItem(Static(f"[link={path}]{title}[/link]\n    {path}")))

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
        """Show search results.

        Args:
            results: List of (title, path) tuples.
        """
        self._results = results
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()
        for title, path in results:
            list_view.append(ListItem(Static(f"[link={path}]{title}[/link]\n    {path}")))

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
```

- [ ] **Step 2: Verify sidebar widget loads**

```bash
python -c "
from deepseek_obsidian.tui.widgets.sidebar import Sidebar, ReferencedNotesPanel, SearchPanel
print('Sidebar widget tests passed')
"
```

- [ ] **Step 3: Commit and push**

```bash
git add src/deepseek_obsidian/tui/widgets/sidebar.py
git commit -m "feat: add sidebar widget with notes panel and vault search"
git push origin main
```

---

### Task 10: Input Bar + Command Hints

**Files:**
- Create: `src/deepseek_obsidian/tui/widgets/input_bar.py`

- [ ] **Step 1: Write the input bar widget**

```python
"""Input bar — text input with send button and command hints."""

from textual.containers import Horizontal, Container
from textual.widgets import Input, Button, Static


class CommandHints(Static):
    """Row of command hints at the bottom of the input area."""

    def __init__(self):
        super().__init__("")

    def on_mount(self) -> None:
        self.update(
            "[dim]/model  /search  /save  /clear  /help[/dim]"
        )


class InputBar(Container):
    """Input area with text field, send button, and command hints."""

    def compose(self):
        with Horizontal(id="input-row"):
            yield Input(
                placeholder="Ask about your notes... or / for commands",
                id="chat-input",
            )
            yield Button("Send", id="send-button", variant="primary")
        yield CommandHints()
```

- [ ] **Step 2: Verify input bar loads**

```bash
python -c "
from deepseek_obsidian.tui.widgets.input_bar import InputBar, CommandHints
print('Input bar tests passed')
"
```

- [ ] **Step 3: Commit and push**

```bash
git add src/deepseek_obsidian/tui/widgets/input_bar.py
git commit -m "feat: add input bar with send button and command hints"
git push origin main
```

---

### Task 11: Header Bar

**Files:**
- Create: `src/deepseek_obsidian/tui/widgets/header.py`

- [ ] **Step 1: Write the header widget**

```python
"""Header bar — shows app title, permission posture, and vault name."""

from textual.containers import Horizontal
from textual.widgets import Static
from textual.reactive import reactive


class Header(Horizontal):
    """Top bar with title, posture indicator, and vault path."""

    posture = reactive("Ask")
    vault_name = reactive("")

    def compose(self):
        yield Static("DeepSeek-Obsidian", id="header-title")
        yield Static("Ask", id="header-posture")
        yield Static("", id="header-vault")

    def watch_posture(self, value: str) -> None:
        posture_label = self.query_one("#header-posture", Static)
        posture_label.update(f"[bold]{value}[/bold]")

    def watch_vault_name(self, value: str) -> None:
        vault_label = self.query_one("#header-vault", Static)
        if value:
            vault_label.update(f"📁 {value}")
```

- [ ] **Step 2: Verify header loads**

```bash
python -c "
from deepseek_obsidian.tui.widgets.header import Header
print('Header widget tests passed')
"
```

- [ ] **Step 3: Commit and push**

```bash
git add src/deepseek_obsidian/tui/widgets/header.py
git commit -m "feat: add header bar with posture indicator and vault name"
git push origin main
```

---

### Task 12: Slash Command System

**Files:**
- Create: `src/deepseek_obsidian/tui/commands.py`
- Create: `tests/test_commands.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for slash command system."""

import pytest
from deepseek_obsidian.tui.commands import (
    Command,
    CommandRegistry,
    parse_command,
)


class TestParseCommand:
    def test_parses_slash_command(self):
        cmd, args = parse_command("/search machine learning")
        assert cmd == "search"
        assert args == "machine learning"

    def test_no_slash_returns_none(self):
        cmd, args = parse_command("hello world")
        assert cmd is None
        assert args == "hello world"

    def test_slash_with_no_args(self):
        cmd, args = parse_command("/help")
        assert cmd == "help"
        assert args == ""

    def test_slash_at_start_only(self):
        cmd, args = parse_command("use /search for searching")
        assert cmd is None
        assert args == "use /search for searching"


class TestCommandRegistry:
    def test_registers_and_finds_command(self):
        registry = CommandRegistry()
        registry.register(Command(name="test", description="Test command", handler=lambda args: "ok"))
        cmd = registry.get("test")
        assert cmd is not None
        assert cmd.name == "test"

    def test_get_nonexistent_returns_none(self):
        registry = CommandRegistry()
        assert registry.get("nonexistent") is None

    def test_list_commands_returns_all(self):
        registry = CommandRegistry()
        registry.register(Command(name="a", description="A", handler=lambda a: None))
        registry.register(Command(name="b", description="B", handler=lambda a: None))
        commands = registry.list_commands()
        assert len(commands) == 2
        names = {c.name for c in commands}
        assert names == {"a", "b"}

    def test_execute_runs_handler(self):
        registry = CommandRegistry()
        results = []
        registry.register(Command(
            name="echo",
            description="Echo back",
            handler=lambda args: results.append(args),
        ))
        registry.execute("echo", "hello")
        assert results == ["hello"]

    def test_execute_unknown_raises(self):
        registry = CommandRegistry()
        with pytest.raises(ValueError, match="Unknown command"):
            registry.execute("nonexistent", "")


class TestCommand:
    def test_command_attributes(self):
        cmd = Command(
            name="search",
            description="Search the vault",
            handler=lambda args: args,
        )
        assert cmd.name == "search"
        assert cmd.description == "Search the vault"
        assert cmd.handler("test") == "test"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_commands.py -v`
Expected: FAIL

- [ ] **Step 3: Write `tui/commands.py`**

```python
"""Slash command system — register, parse, and execute commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


def parse_command(text: str) -> tuple[str | None, str]:
    """Parse a slash command from input text.

    Returns:
        (command_name, args) if the text starts with '/', else (None, raw_text).
    """
    text = text.strip()
    if not text.startswith("/"):
        return None, text

    parts = text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


@dataclass
class Command:
    name: str
    description: str
    handler: Callable[[str], Any]


class CommandRegistry:
    """Registry for slash commands."""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def list_commands(self) -> list[Command]:
        return list(self._commands.values())

    def execute(self, name: str, args: str) -> Any:
        cmd = self.get(name)
        if cmd is None:
            raise ValueError(f"Unknown command: {name}")
        return cmd.handler(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_commands.py -v`
Expected: all 8 tests PASS

- [ ] **Step 5: Commit and push**

```bash
git add src/deepseek_obsidian/tui/commands.py tests/test_commands.py
git commit -m "feat: add slash command parser and registry"
git push origin main
```

---

### Task 13: Diff View for Proposed Edits

**Files:**
- Create: `src/deepseek_obsidian/tui/widgets/diff_view.py`

- [ ] **Step 1: Write the diff view widget**

```python
"""Diff view widget — displays proposed note edits inline with accept/reject."""

from textual.containers import Container, Horizontal
from textual.widgets import Static, Button


class DiffView(Container):
    """Shows a proposed edit as a diff with accept/reject buttons."""

    def __init__(
        self,
        note_title: str,
        old_text: str,
        new_text: str,
        proposal_id: str = "",
    ):
        super().__init__()
        self.note_title = note_title
        self.old_text = old_text
        self.new_text = new_text
        self.proposal_id = proposal_id
        self._accepted: bool | None = None

    def compose(self):
        yield Static(f"[bold]🤖 Proposed edit to \"{self.note_title}\":[/bold]")
        yield Static(f"[red]- {self.old_text}[/red]")
        yield Static(f"[green]+ {self.new_text}[/green]")
        with Horizontal(id="diff-actions"):
            yield Button("Accept", id="diff-accept", variant="success")
            yield Button("Reject", id="diff-reject", variant="error")
            yield Button("Edit Before Accepting", id="diff-edit")

    @property
    def is_accepted(self) -> bool | None:
        return self._accepted

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "diff-accept":
            self._accepted = True
        elif event.button.id == "diff-reject":
            self._accepted = False
        elif event.button.id == "diff-edit":
            self._accepted = None  # caller should handle edit mode
        self.remove()
```

- [ ] **Step 2: Verify diff view loads**

```bash
python -c "
from deepseek_obsidian.tui.widgets.diff_view import DiffView
print('Diff view tests passed')
"
```

- [ ] **Step 3: Commit and push**

```bash
git add src/deepseek_obsidian/tui/widgets/diff_view.py
git commit -m "feat: add diff view widget for proposed note edits"
git push origin main
```

---

### Task 14: Wiring — Connect Engine to TUI (End-to-End)

**Files:**
- Modify: `src/deepseek_obsidian/tui/screen.py`
- Modify: `src/deepseek_obsidian/app.py`

- [ ] **Step 1: Rewrite `app.py` to wire engine + TUI**

```python
"""Application entry point — wires engine to TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer

from deepseek_obsidian.config.loader import load_config
from deepseek_obsidian.engine.vault import VaultReader
from deepseek_obsidian.engine.ai_client import create_client
from deepseek_obsidian.engine.context import ContextBuilder
from deepseek_obsidian.engine.permissions import Permissions, PermissionLevel
from deepseek_obsidian.tui.screen import MainScreen


class DeepSeekTuiApp(App):
    """Main TUI application."""

    CSS = """
    MainScreen {
        layout: grid;
        grid-size: 1;
    }

    #main-layout {
        layout: horizontal;
        height: 1fr;
    }

    #chat-column {
        width: 1fr;
    }

    #sidebar-column {
        width: 35;
        border-left: solid $primary;
    }

    Header {
        dock: top;
        height: 1;
        background: $panel;
        padding: 0 1;
    }

    #header-title {
        width: 1fr;
    }

    #header-posture {
        width: auto;
        padding: 0 1;
        background: $accent;
    }

    #header-vault {
        width: auto;
        padding: 0 1;
    }

    InputBar {
        dock: bottom;
        height: auto;
        background: $panel;
        padding: 0 1;
    }

    #input-row {
        height: 3;
    }

    #chat-input {
        width: 1fr;
    }

    ChatView {
        height: 1fr;
    }

    Sidebar {
        height: 1fr;
    }

    ReferencedNotesPanel {
        height: 1fr;
        border-bottom: solid $primary;
    }

    SearchPanel {
        height: auto;
    }

    .panel-title {
        background: $boost;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("tab", "cycle_permission", "Cycle Permission"),
        ("ctrl+n", "focus_sidebar", "Focus Sidebar"),
        ("ctrl+c", "focus_chat", "Focus Chat"),
        ("ctrl+s", "quick_search", "Quick Search"),
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.permissions = Permissions(
            level=PermissionLevel.from_string(self.config.permission_default)
        )
        self.vault: VaultReader | None = None
        self.ai_client = None
        self.context_builder: ContextBuilder | None = None

    def on_mount(self) -> None:
        # Auto-detect or load vault
        if self.config.vault_path and self.config.vault_path.exists():
            self._load_vault(self.config.vault_path)
        else:
            self._auto_detect_vault()

        if self.ai_client is None:
            self.ai_client = create_client(
                self.config.provider,
                self.config.model,
                api_key=self.config.api_key,
            )

        self.context_builder = ContextBuilder(
            self.vault, max_notes=self.config.max_notes
        ) if self.vault else None

        self.push_screen(MainScreen(self))

    def _load_vault(self, path: Path) -> None:
        self.vault = VaultReader(path, exclude_dirs=self.config.exclude_dirs)

    def _auto_detect_vault(self) -> None:
        """Scan common locations for .obsidian/ directories."""
        search_paths = [
            Path.home() / "Documents",
            Path.home() / "Obsidian",
            Path.home(),
        ]
        candidates: list[Path] = []
        for search_path in search_paths:
            if search_path.exists():
                for obsidian_dir in search_path.rglob(".obsidian"):
                    vault_path = obsidian_dir.parent
                    if vault_path not in candidates:
                        candidates.append(vault_path)

        if len(candidates) == 1:
            self._load_vault(candidates[0])
        elif len(candidates) > 1:
            # For v1: just pick the first one, user can /vault to switch
            self._load_vault(candidates[0])
        # If none found, vault stays None — user will /vault manually

    def action_cycle_permission(self) -> None:
        new_level = self.permissions.cycle()
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.update_posture(new_level.value)

    def action_focus_sidebar(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_sidebar()

    def action_focus_chat(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_chat()

    def action_quick_search(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_search()

    def action_toggle_sidebar(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.toggle_sidebar()


def main() -> None:
    app = DeepSeekTuiApp()
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rewrite `screen.py` to full layout**

```python
"""Main TUI screen with chat-primary layout, sidebar, header, and input bar."""

from textual.screen import Screen
from textual.widgets import Static
from textual.containers import Container
from textual.widget import Widget

from deepseek_obsidian.tui.widgets.header import Header
from deepseek_obsidian.tui.widgets.chat import ChatView
from deepseek_obsidian.tui.widgets.sidebar import Sidebar
from deepseek_obsidian.tui.widgets.input_bar import InputBar
from deepseek_obsidian.tui.commands import CommandRegistry, parse_command


class MainScreen(Screen):
    """Primary screen layout."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._sidebar_visible = True

    def compose(self):
        yield Header()
        with Container(id="main-layout"):
            with Container(id="chat-column"):
                yield ChatView()
            with Container(id="sidebar-column"):
                yield Sidebar()
        yield InputBar()

    def on_mount(self) -> None:
        self._update_header()

    def _update_header(self) -> None:
        header = self.query_one(Header)
        header.posture = self._app.permissions.level.value.title()
        if self._app.vault:
            header.vault_name = self._app.vault.vault_path.name

    def update_posture(self, posture: str) -> None:
        header = self.query_one(Header)
        header.posture = posture.title()
        self._update_header()

    def focus_sidebar(self) -> None:
        sidebar = self.query_one(Sidebar)
        sidebar.focus()

    def focus_chat(self) -> None:
        chat_input = self.query_one("#chat-input")
        chat_input.focus()

    def focus_search(self) -> None:
        search_input = self.query_one("#search-input")
        search_input.focus()

    def toggle_sidebar(self) -> None:
        sidebar_col = self.query_one("#sidebar-column", Container)
        self._sidebar_visible = not self._sidebar_visible
        sidebar_col.display = True if self._sidebar_visible else False

    @property
    def chat_view(self) -> ChatView:
        return self.query_one(ChatView)

    @property
    def sidebar(self) -> Sidebar:
        return self.query_one(Sidebar)

    @property
    def chat_input(self):
        return self.query_one("#chat-input")
```

- [ ] **Step 3: Verify app launches with full layout**

```bash
timeout 3 python -m deepseek_obsidian 2>&1 || true
```
Expected: App launches with header, chat area, sidebar, and input bar visible.

- [ ] **Step 4: Commit and push**

```bash
git add src/deepseek_obsidian/app.py src/deepseek_obsidian/tui/screen.py
git commit -m "feat: wire engine to TUI with full layout and keybindings"
git push origin main
```

---

### Task 15: Slash Command Handlers (Wire All 11 Commands)

**Files:**
- Modify: `src/deepseek_obsidian/tui/screen.py` (add command handling)
- Modify: `src/deepseek_obsidian/app.py` (add command registry)

- [ ] **Step 1: Add command handlers to `app.py`**

Add this method to `DeepSeekTuiApp`:

```python
    def _build_command_registry(self) -> CommandRegistry:
        """Register all slash commands."""
        from deepseek_obsidian.tui.commands import Command, CommandRegistry

        registry = CommandRegistry()

        registry.register(Command(
            name="model",
            description="Switch AI provider/model",
            handler=self._cmd_model,
        ))
        registry.register(Command(
            name="search",
            description="Search the vault",
            handler=self._cmd_search,
        ))
        registry.register(Command(
            name="open",
            description="Open a note by [[wikilink]]",
            handler=self._cmd_open,
        ))
        registry.register(Command(
            name="save",
            description="Save last AI response as a note",
            handler=self._cmd_save,
        ))
        registry.register(Command(
            name="link",
            description="Create a wikilink between two notes",
            handler=self._cmd_link,
        ))
        registry.register(Command(
            name="vault",
            description="Switch to a different vault",
            handler=self._cmd_vault,
        ))
        registry.register(Command(
            name="export",
            description="Export chat to markdown",
            handler=self._cmd_export,
        ))
        registry.register(Command(
            name="clear",
            description="Clear current chat",
            handler=self._cmd_clear,
        ))
        registry.register(Command(
            name="theme",
            description="Switch TUI theme",
            handler=self._cmd_theme,
        ))
        registry.register(Command(
            name="perm",
            description="Set permission posture",
            handler=self._cmd_perm,
        ))
        registry.register(Command(
            name="help",
            description="Show available commands",
            handler=self._cmd_help,
        ))
        return registry

    def _cmd_model(self, args: str) -> str:
        """Switch AI provider/model. Usage: /model deepseek deepseek-chat"""
        parts = args.split()
        if len(parts) >= 1:
            provider = parts[0]
            model = parts[1] if len(parts) > 1 else None
            self.config.provider = provider
            if model:
                self.config.model = model
            self.ai_client = create_client(
                provider,
                model or "deepseek-chat",
                api_key=self.config.api_key,
            )
            return f"Switched to {provider}/{model or 'default'}"
        return "Usage: /model <provider> [model]"

    def _cmd_search(self, args: str) -> str:
        """Search the vault and show results in sidebar."""
        if not self.vault or not args:
            return "No vault loaded or no query provided."
        results = self.vault.search_full_text(args)
        screen = self.screen
        if isinstance(screen, MainScreen):
            notes_data = [(n.title, str(n.path)) for n in results[:20]]
            screen.sidebar.search_panel.set_results(notes_data)
        return f"Found {len(results)} notes matching '{args}'."

    def _cmd_open(self, args: str) -> str:
        """Open a note by wikilink. Usage: /open [[Note Title]]"""
        if not self.vault or not args:
            return "No vault loaded or no note specified."
        link = args.strip().strip("[[").strip("]]")
        note = self.vault.resolve_wikilink(link)
        if note:
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.sidebar.notes_panel.set_notes([(note.title, str(note.path))])
            return f"Opened: {note.title}"
        return f"Note not found: {link}"

    def _cmd_save(self, args: str) -> str:
        """Save last AI response as a new note. Usage: /save [filename]"""
        if not self.vault:
            return "No vault loaded."
        if not self.permissions.can_write():
            return "Cannot save: permission level is Ask. Switch to Full Access."
        # Get last assistant message from chat
        screen = self.screen
        if isinstance(screen, MainScreen) and screen.chat_view._current_assistant_message:
            content = screen.chat_view._current_assistant_message.content
        else:
            return "No AI response to save."
        filename = args.strip() if args.strip() else "untitled.md"
        filepath = self.vault.vault_path / filename
        filepath.write_text(content)
        self.permissions.audit_trail.record("write", filename, "Created note from AI response")
        return f"Saved to {filename}"

    def _cmd_link(self, args: str) -> str:
        """Create a wikilink. Usage: /link Note A -> Note B"""
        if not self.vault:
            return "No vault loaded."
        if "->" not in args:
            return "Usage: /link <from> -> <to>"
        from_note, to_note = args.split("->", 1)
        from_note = from_note.strip()
        to_note = to_note.strip()
        if not self.permissions.can_write():
            return f"Would link [[{from_note}]] -> [[{to_note}]] (Full Access required to write)."
        note = self.vault.resolve_wikilink(from_note)
        if note:
            content = note.content + f"\n\nSee also: [[{to_note}]]"
            note.path.write_text(content)
            self.permissions.audit_trail.record("write", str(note.path), f"Added link to [[{to_note}]]")
            return f"Linked [[{from_note}]] -> [[{to_note}]]"
        return f"Note not found: {from_note}"

    def _cmd_vault(self, args: str) -> str:
        """Switch vault. Usage: /vault /path/to/vault"""
        path = Path(args.strip()).expanduser()
        if path.exists() and (path / ".obsidian").exists():
            self._load_vault(path)
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen._update_header()
            return f"Switched to vault: {path.name}"
        return f"Not a valid Obsidian vault: {path}"

    def _cmd_export(self, args: str) -> str:
        """Export chat to markdown file. Usage: /export ~/chat-export.md"""
        path = Path(args.strip()).expanduser() if args.strip() else Path.home() / "deepseek-chat-export.md"
        screen = self.screen
        if isinstance(screen, MainScreen):
            lines = []
            for child in screen.chat_view.children:
                if hasattr(child, 'content'):
                    role = getattr(child, 'role', 'unknown')
                    lines.append(f"## {role}\n\n{child.content}\n")
            path.write_text("\n---\n".join(lines))
            return f"Chat exported to {path}"
        return "Nothing to export."

    def _cmd_clear(self, args: str) -> str:
        """Clear the chat (with save option)."""
        screen = self.screen
        if isinstance(screen, MainScreen):
            if args.strip() == "--save":
                self._cmd_export("")
            screen.chat_view.clear_chat()
            if self.context_builder:
                self.context_builder.history.clear()
            return "Chat cleared."
        return "OK"

    def _cmd_theme(self, args: str) -> str:
        """Switch theme. Usage: /theme dracula"""
        theme = args.strip()
        available = ["dracula", "nord", "catppuccin", "monokai"]
        if theme in available:
            self.theme = theme
            return f"Theme changed to {theme}."
        return f"Available themes: {', '.join(available)}"

    def _cmd_perm(self, args: str) -> str:
        """Set permission posture. Usage: /perm ask|review|full"""
        try:
            level = PermissionLevel.from_string(args.strip())
            self.permissions.set_level(level)
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.update_posture(level.value)
            return f"Permission set to: {level.value}"
        except ValueError:
            return "Usage: /perm ask|review|full"

    def _cmd_help(self, args: str) -> str:
        """Show available commands."""
        lines = ["Available commands:", ""]
        for cmd in self._command_registry.list_commands():
            lines.append(f"  /{cmd.name} — {cmd.description}")
        lines.extend([
            "",
            "Keybindings:",
            "  Tab — Cycle permission posture",
            "  Ctrl+N — Focus sidebar",
            "  Ctrl+C — Focus chat",
            "  Ctrl+S — Quick vault search",
            "  Ctrl+B — Toggle sidebar",
        ])
        return "\n".join(lines)
```

- [ ] **Step 2: Wire command handling into `on_mount` of `DeepSeekTuiApp`**

Add `self._command_registry = self._build_command_registry()` to `on_mount`.

- [ ] **Step 3: Add input submission handling to `MainScreen`**

Add to `MainScreen`:

```python
    def on_input_submitted(self, event) -> None:
        """Handle Enter in the chat input."""
        if event.input.id != "chat-input":
            return
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        cmd_name, cmd_args = parse_command(text)

        if cmd_name:
            # Slash command
            registry = self._app._command_registry
            try:
                result = registry.execute(cmd_name, cmd_args)
                if result and isinstance(result, str):
                    self.chat_view.add_user_message(f"/{cmd_name} {cmd_args}")
                    msg = self.chat_view
                    msg.start_assistant_message()
                    msg.stream_chunk(result)
                    msg.finish_assistant_message()
            except ValueError as e:
                self.chat_view.add_user_message(text)
                msg = self.chat_view
                msg.start_assistant_message()
                msg.stream_chunk(str(e))
                msg.finish_assistant_message()
        else:
            # Regular chat message
            self.chat_view.add_user_message(text)
            # TODO: in a later task, call AI client here
```

- [ ] **Step 4: Verify commands work via import**

```bash
python -c "
from deepseek_obsidian.tui.commands import parse_command
cmd, args = parse_command('/search test query')
assert cmd == 'search'
assert args == 'test query'
cmd, args = parse_command('regular chat')
assert cmd is None
print('Command parsing tests passed')
"
```

- [ ] **Step 5: Commit and push**

```bash
git add src/deepseek_obsidian/app.py src/deepseek_obsidian/tui/screen.py
git commit -m "feat: wire all 11 slash command handlers"
git push origin main
```

---

### Task 16: AI Chat Flow — Send Messages and Stream Responses

**Files:**
- Modify: `src/deepseek_obsidian/tui/screen.py`
- Modify: `src/deepseek_obsidian/app.py`

- [ ] **Step 1: Add async message sending to `MainScreen.on_input_submitted`**

Replace the `# TODO: in a later task` comment in the `else` branch with:

```python
        else:
            # Regular chat message
            self.chat_view.add_user_message(text)

            if self._app.context_builder and self._app.ai_client:
                import asyncio
                asyncio.create_task(self._send_to_ai(text))
```

- [ ] **Step 2: Add `_send_to_ai` method to `MainScreen`**

```python
    async def _send_to_ai(self, text: str) -> None:
        """Send user message to AI and stream the response."""
        if not self._app.context_builder or not self._app.ai_client:
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk("No vault or AI client configured. Use /vault to set up a vault.")
            self.chat_view.finish_assistant_message()
            return

        # Build context
        messages, context_notes = self._app.context_builder.build(
            text,
            permission_level=self._app.permissions.level.value,
        )

        # Update referenced notes in sidebar
        notes_data = [(n.title, str(n.path)) for n in context_notes]
        self.sidebar.notes_panel.set_notes(notes_data)

        # Stream AI response
        self.chat_view.start_assistant_message()
        try:
            async for chunk in self._app.ai_client.stream(messages):
                if chunk.content:
                    self.chat_view.stream_chunk(chunk.content)
        except Exception as e:
            self.chat_view.stream_chunk(f"\n\n[red]Error: {e}[/red]")

        self.chat_view.finish_assistant_message()

        # Add to chat history
        if self.chat_view._current_assistant_message:
            self._app.context_builder.history.add(
                Message(role="user", content=text)
            )
            # Note: we need the final content. The current assistant message
            # has already been finished, so we'd need to track the last content.
            # For v1: store the last assistant response content.
```

Wait, there's a bug — `finish_assistant_message()` sets `_current_assistant_message = None`, so the history addition won't work. Let me fix this by storing the content before finishing.

Actually let me restructure — track the full content in a local variable during streaming:

```python
    async def _send_to_ai(self, text: str) -> None:
        """Send user message to AI and stream the response."""
        if not self._app.context_builder or not self._app.ai_client:
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk("No vault or AI client configured. Use /vault to set up a vault.")
            self.chat_view.finish_assistant_message()
            return

        messages, context_notes = self._app.context_builder.build(
            text,
            permission_level=self._app.permissions.level.value,
        )

        notes_data = [(n.title, str(n.path)) for n in context_notes]
        self.sidebar.notes_panel.set_notes(notes_data)

        self.chat_view.start_assistant_message()
        full_response = ""
        try:
            async for chunk in self._app.ai_client.stream(messages):
                if chunk.content:
                    full_response += chunk.content
                    self.chat_view.stream_chunk(chunk.content)
        except Exception as e:
            error_msg = f"\n\n[red]Error: {e}[/red]"
            full_response += error_msg
            self.chat_view.stream_chunk(error_msg)
        self.chat_view.finish_assistant_message()

        self._app.context_builder.history.add(Message(role="user", content=text))
        self._app.context_builder.history.add(Message(role="assistant", content=full_response))
```

And add the import for `Message` at top of `screen.py`:

```python
from deepseek_obsidian.engine.ai_client import Message
```

- [ ] **Step 3: Verify end-to-end flow (with mock or dry run)**

```bash
python -c "
from deepseek_obsidian.engine.context import ContextBuilder, ChatHistory
from deepseek_obsidian.engine.ai_client import Message
from deepseek_obsidian.engine.vault import VaultReader, scan_vault
from pathlib import Path
import tempfile

# Create temp vault and verify context building works
with tempfile.TemporaryDirectory() as tmp:
    vault_path = Path(tmp)
    (vault_path / '.obsidian').mkdir()
    (vault_path / 'test.md').write_text('# Test Note\n\nContent here.')
    vault = VaultReader(vault_path)
    builder = ContextBuilder(vault, max_notes=5)
    messages, notes = builder.build('test query')
    assert len(messages) >= 2
    assert messages[-1].content == 'test query'
    print('End-to-end context building works')
"
```

- [ ] **Step 4: Commit and push**

```bash
git add src/deepseek_obsidian/tui/screen.py src/deepseek_obsidian/app.py
git commit -m "feat: wire AI chat flow with streaming responses and context building"
git push origin main
```

---

### Task 17: Themes (Built-in Dracula, Nord, Catppuccin, Monokai)

**Files:**
- Create: `src/deepseek_obsidian/themes/__init__.py`
- Create: `src/deepseek_obsidian/themes/builtins.py`

- [ ] **Step 1: Write built-in themes**

```python
"""Built-in TUI themes."""

THEMES: dict[str, dict] = {
    "dracula": {
        "name": "dracula",
        "dark": True,
        "primary": "#bd93f9",
        "secondary": "#ff79c6",
        "accent": "#50fa7b",
        "warning": "#ffb86c",
        "error": "#ff5555",
        "success": "#50fa7b",
        "surface": "#282a36",
        "panel": "#44475a",
        "boost": "#6272a4",
        "text": "#f8f8f2",
    },
    "nord": {
        "name": "nord",
        "dark": True,
        "primary": "#88c0d0",
        "secondary": "#81a1c1",
        "accent": "#a3be8c",
        "warning": "#d08770",
        "error": "#bf616a",
        "success": "#a3be8c",
        "surface": "#2e3440",
        "panel": "#3b4252",
        "boost": "#4c566a",
        "text": "#eceff4",
    },
    "catppuccin": {
        "name": "catppuccin",
        "dark": True,
        "primary": "#cba6f7",
        "secondary": "#f5c2e7",
        "accent": "#a6e3a1",
        "warning": "#fab387",
        "error": "#f38ba8",
        "success": "#a6e3a1",
        "surface": "#1e1e2e",
        "panel": "#313244",
        "boost": "#45475a",
        "text": "#cdd6f4",
    },
    "monokai": {
        "name": "monokai",
        "dark": True,
        "primary": "#a6e22e",
        "secondary": "#f92672",
        "accent": "#66d9ef",
        "warning": "#e6db74",
        "error": "#f92672",
        "success": "#a6e22e",
        "surface": "#272822",
        "panel": "#3e3d32",
        "boost": "#75715e",
        "text": "#f8f8f2",
    },
}
```

- [ ] **Step 2: Verify themes are valid**

```bash
python -c "
from deepseek_obsidian.themes.builtins import THEMES
assert len(THEMES) == 4
for name, theme in THEMES.items():
    assert 'primary' in theme
    assert 'surface' in theme
    assert 'text' in theme
print(f'{len(THEMES)} themes validated')
"
```

- [ ] **Step 3: Commit and push**

```bash
git add src/deepseek_obsidian/themes/
git commit -m "feat: add built-in themes (dracula, nord, catppuccin, monokai)"
git push origin main
```

---

### Task 18: CI/CD — GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint with ruff
        run: ruff check src/ tests/

      - name: Type check with mypy
        run: mypy src/

      - name: Test with pytest
        run: pytest -v --cov=deepseek_obsidian --cov-report=term-missing
```

- [ ] **Step 2: Push and verify CI runs**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for lint, type-check, and test"
git push origin main
```

- [ ] **Step 3: Check CI status**

After push, verify the workflow runs green at `https://github.com/Shyboy0499/DeepSeek-Obsidian/actions`.

---

## Summary: PR Order

| # | PR Title | Files |
|---|----------|-------|
| 1 | Project scaffold + tooling | pyproject.toml, __init__.py, __main__.py, .gitignore |
| 2 | Config system | config/*, tests/test_config.py |
| 3 | Vault reader | engine/vault.py, tests/conftest.py, tests/test_vault.py |
| 4 | Permission model + audit trail | engine/permissions.py, tests/test_permissions.py |
| 5 | AI client (multi-provider + streaming) | engine/ai_client.py, tests/test_ai_client.py |
| 6 | Context builder | engine/context.py, tests/test_context.py |
| 7 | TUI scaffold + main screen | app.py, tui/screen.py, tui widgets __init__ |
| 8 | Chat widget | tui/widgets/chat.py |
| 9 | Sidebar widget | tui/widgets/sidebar.py |
| 10 | Input bar + command hints | tui/widgets/input_bar.py |
| 11 | Header bar | tui/widgets/header.py |
| 12 | Slash command system | tui/commands.py, tests/test_commands.py |
| 13 | Diff view widget | tui/widgets/diff_view.py |
| 14 | Engine ↔ TUI wiring | app.py, screen.py (rewrites) |
| 15 | Slash command handlers | app.py, screen.py (add handlers) |
| 16 | AI chat flow (streaming) | screen.py, app.py |
| 17 | Themes | themes/builtins.py |
| 18 | CI/CD | .github/workflows/ci.yml |

Each PR is a self-contained, testable change that can be merged independently. Stacked roughly in dependency order — core engine first, then TUI widgets, then wiring.
