"""Tests for config loading and defaults."""

import os
import tempfile
from pathlib import Path

from deepseek_obsidian.config.defaults import DEFAULTS
from deepseek_obsidian.config.loader import load_config


class TestDefaults:
    def test_default_vault_path_is_none(self):
        assert DEFAULTS["vault"]["path"] is None

    def test_default_provider_is_deepseek(self):
        assert DEFAULTS["model"]["provider"] == "deepseek"
        assert DEFAULTS["model"]["model"] == "deepseek-v4-flash"

    def test_default_permission_is_ask(self):
        assert DEFAULTS["tui"]["permission_default"] == "ask"

    def test_default_max_notes_is_10(self):
        assert DEFAULTS["context"]["max_notes"] == 10


class TestLoadConfig:
    def test_loads_defaults_when_no_config_file(self):
        config = load_config(config_path=Path("/nonexistent/path/config.toml"))
        assert config.vault_path is None
        assert config.provider == "deepseek"
        assert config.model == "deepseek-v4-flash"

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
