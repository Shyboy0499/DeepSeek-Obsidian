"""Configuration loader — reads TOML config and environment variables."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepseek_tui.config.defaults import DEFAULTS

CONFIG_DIR = Path.home() / ".config" / "deepseek-tui"
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
