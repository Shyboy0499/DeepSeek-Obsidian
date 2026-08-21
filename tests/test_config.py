"""Tests for config loading and defaults."""

import os
import tempfile
from pathlib import Path

import deepseek_obsidian.config.loader as loader_module
from deepseek_obsidian.config.defaults import DEFAULTS
from deepseek_obsidian.config.loader import load_config, save_vault_path


class TestDefaults:
    def test_default_vault_path_is_none(self):
        assert DEFAULTS["vault"]["path"] is None

    def test_default_provider_is_deepseek(self):
        assert DEFAULTS["model"]["provider"] == "deepseek"
        assert DEFAULTS["model"]["model"] == "deepseek-v4-pro"

    def test_default_permission_is_ask(self):
        assert DEFAULTS["tui"]["permission_default"] == "ask"

    def test_default_max_notes_is_10(self):
        assert DEFAULTS["context"]["max_notes"] == 10


class TestLoadConfig:
    def test_loads_defaults_when_no_config_file(self):
        config = load_config(config_path=Path("/nonexistent/path/config.toml"))
        assert config.vault_path is None
        assert config.provider == "deepseek"
        assert config.model == "deepseek-v4-pro"

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


class TestSaveVaultPath:
    def test_preserves_exclude_dirs_list(self, monkeypatch, tmp_path):
        monkeypatch.setattr(loader_module, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(loader_module, "CONFIG_PATH", tmp_path / "config.toml")
        loader_module.CONFIG_PATH.write_text(
            '[vault]\nexclude_dirs = [".git", "_templates"]\n\n[model]\nprovider = "deepseek"\n'
        )
        save_vault_path("/tmp/my-vault")
        import tomllib
        data = tomllib.loads(loader_module.CONFIG_PATH.read_text())
        assert data["vault"]["exclude_dirs"] == [".git", "_templates"]
        assert data["vault"]["path"] == "/tmp/my-vault"
        assert data["model"]["provider"] == "deepseek"

    def test_creates_config_if_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(loader_module, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(loader_module, "CONFIG_PATH", tmp_path / "config.toml")
        save_vault_path("/tmp/v")
        assert loader_module.CONFIG_PATH.exists()
        import tomllib
        data = tomllib.loads(loader_module.CONFIG_PATH.read_text())
        assert data["vault"]["path"] == "/tmp/v"

    def test_updates_existing_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(loader_module, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(loader_module, "CONFIG_PATH", tmp_path / "config.toml")
        loader_module.CONFIG_PATH.write_text('[vault]\npath = "/old"\n')
        save_vault_path("/new")
        import tomllib
        data = tomllib.loads(loader_module.CONFIG_PATH.read_text())
        assert data["vault"]["path"] == "/new"


class TestSaveModelConfig:
    def test_saves_provider_and_model(self, monkeypatch, tmp_path):
        monkeypatch.setattr(loader_module, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(loader_module, "CONFIG_PATH", tmp_path / "config.toml")
        from deepseek_obsidian.config.loader import save_model_config
        save_model_config("openai", "gpt-4o")
        import tomllib
        data = tomllib.loads(loader_module.CONFIG_PATH.read_text())
        assert data["model"]["provider"] == "openai"
        assert data["model"]["model"] == "gpt-4o"
