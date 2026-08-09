"""Summative integration tests — end-to-end with a real vault.

These validate that all layers (config → vault → context → AI client)
work together correctly. Run before release.
"""

import tempfile
from pathlib import Path

import pytest

from deepseek_obsidian.engine.ai_client import AIClient, AIProvider
from deepseek_obsidian.engine.context import ContextBuilder
from deepseek_obsidian.engine.permissions import PermissionLevel, Permissions
from deepseek_obsidian.engine.vault import VaultReader


@pytest.fixture
def integration_vault():
    """A realistic vault with interlinked notes."""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        (vault / ".obsidian").mkdir()

        (vault / "alice.md").write_text("""---
title: Alice's Research
tags: [research, ml]
---

# Alice's Research

Working on [[machine learning]] with [[bob]]. Key findings in [[results]].
""")
        (vault / "bob.md").write_text("""---
title: Bob's Notes
tags: [notes]
---

# Bob's Notes

Collaborating with [[alice's research]] on the ML project.
See [[results]] for outcomes.
""")
        (vault / "results.md").write_text("""# Results

Accuracy: 94%. Referenced by [[alice's research]] and [[bob's notes]].
""")
        (vault / "machine learning.md").write_text("""# Machine Learning

Fundamentals of ML. Referenced by [[alice's research]].
""")
        # Excluded folder
        trash = vault / ".trash"
        trash.mkdir()
        (trash / "deleted.md").write_text("# Deleted note")
        yield vault


class TestEndToEndVaultFlow:
    """The full pipeline: config → vault → context → AI."""

    def test_full_pipeline_loads_and_searches(self, integration_vault):
        vault = VaultReader(integration_vault, exclude_dirs=[".trash"])
        assert len(vault.notes) == 4
        assert ".trash" not in {n.path.parent.name for n in vault.notes}

    def test_backlinks_resolve_across_notes(self, integration_vault):
        vault = VaultReader(integration_vault)
        backlinks = vault.backlinks("results")
        titles = {n.title for n in backlinks}
        assert "Alice's Research" in titles
        assert "Bob's Notes" in titles

    def test_wikilink_chains_resolve(self, integration_vault):
        vault = VaultReader(integration_vault)
        alice = vault.resolve_wikilink("alice's research")
        assert alice is not None
        # Alice links to ML
        links = alice.wikilinks()
        assert "machine learning" in links
        # ML resolves
        ml = vault.resolve_wikilink("machine learning")
        assert ml is not None

    def test_context_builder_includes_linked_notes(self, integration_vault):
        vault = VaultReader(integration_vault)
        builder = ContextBuilder(vault, max_notes=10)
        messages, ctx = builder.build("tell me about [[alice's research]]")
        titles = {n.title for n in ctx}
        assert "Alice's Research" in titles  # Linked note always included

    def test_permission_gates_before_writes(self, integration_vault):
        perms = Permissions(PermissionLevel.ASK)
        assert not perms.can_write()
        perms.cycle()  # review
        assert not perms.can_write()
        perms.cycle()  # full
        assert perms.can_write()

    def test_system_prompt_builds_with_context(self, integration_vault):
        vault = VaultReader(integration_vault)
        client = AIClient(AIProvider.DEEPSEEK, "deepseek-v4-flash")
        alice = vault.resolve_wikilink("alice's research")
        prompt = client.build_system_prompt([alice] if alice else [], "ask")
        assert "Alice's Research" in prompt.content
        assert "machine learning" in prompt.content
        assert "already loaded" in prompt.content.lower()

    def test_audit_trail_survives_roundtrip(self, integration_vault):
        from deepseek_obsidian.engine.permissions import AuditTrail

        trail = AuditTrail()
        trail.record("write", "alice.md", "added link", previous_content="old")
        trail.record("write", "bob.md", "fixed typo", previous_content="old bob")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            trail.save(Path(f.name))
            fp = f.name

        loaded = AuditTrail.load(Path(fp))
        Path(fp).unlink()

        assert len(loaded.entries) == 2
        assert loaded.entries[0].target == "alice.md"
        assert loaded.entries[1].target == "bob.md"
