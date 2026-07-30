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

        (vault / "note1.md").write_text("""---
title: Machine Learning Basics
tags: [ml, beginner]
---

# Machine Learning Basics

This is about [[neural networks]] and [[deep learning]].

Some content here.
""")

        (vault / "note2.md").write_text("""# Neural Networks

Neural networks are the foundation of [[deep learning]].

Backpropagation is key to training.
""")

        subdir = vault / "topics"
        subdir.mkdir()
        (subdir / "deep-learning.md").write_text("""---
title: Deep Learning
tags: [ml, advanced]
---

# Deep Learning

Building on [[machine learning basics]] and [[neural networks]].
""")

        (vault / "image.png").write_text("fake image")

        excluded = vault / "_templates"
        excluded.mkdir()
        (excluded / "template.md").write_text("# Template Note")

        yield vault
