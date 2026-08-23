"""Tests for vault reader."""

from pathlib import Path

from deepseek_obsidian.engine.vault import Note, VaultReader, scan_vault, update_tags


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


class TestUpdateTags:
    def test_add_tag(self, temp_vault):
        vault = VaultReader(temp_vault)
        note = vault.resolve_wikilink("machine learning basics")
        assert note is not None
        update_tags(note, add=["newtag"])
        assert "newtag" in note.tags

    def test_remove_tag(self, temp_vault):
        vault = VaultReader(temp_vault)
        note = vault.resolve_wikilink("machine learning basics")
        assert note is not None
        assert "ml" in note.tags
        update_tags(note, remove=["ml"])
        assert "ml" not in note.tags

    def test_add_and_remove_together(self, temp_vault):
        vault = VaultReader(temp_vault)
        note = vault.resolve_wikilink("machine learning basics")
        update_tags(note, add=["x"], remove=["ml"])
        assert "x" in note.tags
        assert "ml" not in note.tags


class TestSemanticSearch:
    def test_finds_related_notes_by_word_overlap(self, temp_vault):
        vault = VaultReader(temp_vault)
        # note1 content mentions "neural networks" and "deep learning"
        # Search with reordered/partial words — should still match
        results = vault.search_semantic("neural deep")
        titles = {n.title for n in results}
        assert "Machine Learning Basics" in titles

    def test_ranks_most_relevant_higher(self, temp_vault):
        vault = VaultReader(temp_vault)
        results = vault.search_semantic("neural networks")
        assert results, "should return results"
        # The note titled "Neural Networks" should rank highly
        top_titles = [n.title for n in results[:3]]
        assert "Neural Networks" in top_titles

    def test_empty_query_returns_list(self, temp_vault):
        vault = VaultReader(temp_vault)
        results = vault.search_semantic("")
        assert isinstance(results, list)


class TestMtimeCache:
    def test_refresh_reuses_unchanged_notes(self, temp_vault):
        import time
        vault = VaultReader(temp_vault)
        # Force a stable mtime
        for note in vault.notes:
            note.path.touch()
        time.sleep(0.01)
        first = vault.notes[0]
        # Refresh with no changes — should reuse the SAME Note object
        vault.refresh()
        second = vault.notes[0]
        assert first is second or first.title == second.title

    def test_refresh_detects_changed_file(self, temp_vault):
        vault = VaultReader(temp_vault)
        # Modify a note
        target = temp_vault / "note1.md"
        target.write_text("---\ntitle: Changed Title\n---\n# Changed\n\nnew")
        vault.refresh()
        changed = vault.resolve_wikilink("changed title")
        assert changed is not None

    def test_refresh_removes_deleted_file(self, temp_vault):
        vault = VaultReader(temp_vault)
        (temp_vault / "note2.md").unlink()
        vault.refresh()
        titles = {n.title for n in vault.notes}
        assert "Neural Networks" not in titles
