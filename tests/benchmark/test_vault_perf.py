"""Benchmark tests — detect performance regressions.

Run with: pytest tests/benchmark/ -v
Skip in CI if too slow: @pytest.mark.skipif(os.getenv("CI"), reason="benchmark")
"""

import tempfile
import time
from pathlib import Path

from deepseek_obsidian.engine.vault import VaultReader, scan_vault


def _make_vault(num_notes: int, with_frontmatter: bool = False) -> Path:
    """Create a synthetic vault with N notes."""
    tmp = tempfile.mkdtemp()
    vault = Path(tmp)
    (vault / ".obsidian").mkdir()
    for i in range(num_notes):
        content = f"# Note {i}\n\nBody text for note {i}.\n" * 5
        if with_frontmatter:
            content = (
                f'---\ntitle: Note {i}\ntags: [tag{i % 5}]\n---\n' + content
            )
        (vault / f"note_{i}.md").write_text(content)
    # Add excluded dirs with files
    trash = vault / ".trash"
    trash.mkdir()
    for i in range(10):
        (trash / f"trash_{i}.md").write_text("# trash")
    return vault


class TestVaultScanBenchmark:
    """Performance must not regress beyond these thresholds."""

    def test_scan_100_notes_under_10ms(self):
        """100 notes should scan in under 10ms."""
        vault = _make_vault(100)
        start = time.perf_counter()
        _ = scan_vault(vault, exclude_dirs=[".trash"])
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 10, f"100 notes took {elapsed_ms:.1f}ms (limit 10ms)"

    def test_scan_500_notes_under_50ms(self):
        """500 notes should scan in under 50ms."""
        vault = _make_vault(500)
        start = time.perf_counter()
        _ = scan_vault(vault)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"500 notes took {elapsed_ms:.1f}ms (limit 50ms)"

    def test_scan_with_frontmatter_under_100ms(self):
        """500 notes with YAML frontmatter under 100ms."""
        vault = _make_vault(500, with_frontmatter=True)
        start = time.perf_counter()
        _ = scan_vault(vault)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, (
            f"500 frontmatter notes took {elapsed_ms:.1f}ms (limit 100ms)"
        )

    def test_excluded_dirs_not_scanned(self):
        """Excluded directories should not appear in results."""
        vault = _make_vault(50)
        notes = scan_vault(vault, exclude_dirs=[".trash"])
        paths = {n.path.parent.name for n in notes}
        assert ".trash" not in paths

    def test_vault_reader_indexes_correctly(self):
        """VaultReader should index all notes, excluding trash."""
        vault = _make_vault(100)
        reader = VaultReader(vault, exclude_dirs=[".trash"])
        assert len(reader.notes) == 100


class TestVaultSearchBenchmark:
    """Search must not regress."""

    def test_full_text_search_under_1ms(self):
        """Full-text search across 100 notes under 1ms."""
        vault = _make_vault(100)
        reader = VaultReader(vault)
        start = time.perf_counter()
        results = reader.search_full_text("Note 50")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert len(results) > 0
        assert elapsed_ms < 1, f"Search took {elapsed_ms:.1f}ms (limit 1ms)"
