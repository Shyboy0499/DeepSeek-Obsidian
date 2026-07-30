"""Tests for vault reader."""

from pathlib import Path
from deepseek_tui.engine.vault import VaultReader, Note, scan_vault


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
        assert "image.png" not in paths

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
        titles = {n.title for n in backlinks}
        assert "Machine Learning Basics" in titles
        assert "Deep Learning" in titles

    def test_resolve_wikilink_finds_note_by_slug(self, temp_vault):
        vault = VaultReader(temp_vault)
        note = vault.resolve_wikilink("neural networks")
        assert note is not None
        assert note.title == "Neural Networks"
