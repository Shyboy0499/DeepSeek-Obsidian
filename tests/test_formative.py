"""Formative tests — run during development to catch issues early.

These are fast, focused tests you run after every change. They validate
that the component under development behaves correctly against real data.
"""

import os
import tempfile
from pathlib import Path

import pytest
from deepseek_obsidian.config.loader import Config, load_config
from deepseek_obsidian.engine.permissions import AuditTrail
from deepseek_obsidian.engine.ai_client import AIProvider
from deepseek_obsidian.tui.commands import parse_command, CommandRegistry, Command


class TestConfigFormative:
    """Catch config issues before they reach production."""

    def test_no_config_file_produces_sensible_defaults(self):
        config = load_config(config_path=Path("/nonexistent/x.toml"))
        assert config.provider == "deepseek"
        assert config.permission_default == "ask"
        assert config.max_notes == 10

    def test_model_switch_preserves_other_settings(self):
        """Changing model shouldn't affect vault config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[vault]\npath = "/tmp/v"\n[model]\nprovider = "openai"\n')
            path = f.name
        config = load_config(config_path=Path(path))
        os.unlink(path)
        # Vault settings preserved
        assert config.vault_path == Path("/tmp/v")
        # Model changed
        assert config.provider == "openai"


class TestAuditFormative:
    """Make sure the audit trail is correct during development."""

    def test_multiple_writes_then_undo_restores_order(self):
        trail = AuditTrail()
        trail.record("write", "a.md", "first", previous_content="orig_a")
        trail.record("write", "b.md", "second", previous_content="orig_b")
        # Undo most recent first
        last = trail.pop_last_write()
        assert last.target == "b.md"
        assert last.previous_content == "orig_b"
        # Undo next
        first = trail.pop_last_write()
        assert first.target == "a.md"
        # Nothing left
        assert trail.pop_last_write() is None

    def test_non_write_entries_dont_block_undo(self):
        trail = AuditTrail()
        trail.record("read", "a.md", "")  # read — shouldn't block
        trail.record("write", "a.md", "change", previous_content="orig")
        trail.record("read", "b.md", "")
        entry = trail.pop_last_write()
        assert entry.target == "a.md"  # Found the write, skipped reads


class TestCommandFormative:
    """Catch command parsing regressions."""

    def test_command_with_multiple_args(self):
        cmd, args = parse_command("/model openai gpt-4o")
        assert cmd == "model"
        assert args == "openai gpt-4o"

    def test_slash_in_middle_is_not_command(self):
        cmd, args = parse_command("use /search for this")
        assert cmd is None
        assert args == "use /search for this"

    def test_empty_input(self):
        cmd, args = parse_command("")
        assert cmd is None
        assert args == ""

    def test_command_registry_executes_correct_handler(self):
        results = []
        reg = CommandRegistry()
        reg.register(Command("echo", "Echo", lambda a: results.append(a)))
        reg.execute("echo", "test123")
        assert results == ["test123"]


class TestProviderFormative:
    """Catch model configuration issues."""

    def test_all_providers_have_known_models(self):
        models = AIProvider.known_models()
        for provider in AIProvider:
            assert provider.value in models
            assert len(models[provider.value]) >= 1

    def test_deepseek_models_match_api(self):
        models = AIProvider.known_models()["deepseek"]
        assert "deepseek-v4-flash" in models
        assert "deepseek-v4-pro" in models
        # Only v4 models, no old aliases
        assert "deepseek-chat" not in models
        assert "deepseek-reasoner" not in models
