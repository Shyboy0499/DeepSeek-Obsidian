"""Configuration loader — reads TOML config and environment variables."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepseek_obsidian.config.defaults import DEFAULTS

CONFIG_DIR = Path.home() / ".config" / "deepseek-obsidian"
CONFIG_PATH = CONFIG_DIR / "config.toml"


def save_vault_path(path: str) -> None:
    """Persist the chosen vault path to config.toml.

    Uses targeted line replacement so other settings (lists, nested values)
    are preserved exactly as written.
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            CONFIG_PATH.write_text(f'[vault]\npath = "{path}"\n')
            return

        lines = CONFIG_PATH.read_text().splitlines()
        out: list[str] = []
        in_vault_section = False
        path_written = False
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("[") and line.endswith("]"):
                in_vault_section = line == "[vault]"
                out.append(lines[i])
                i += 1
                # If entering vault section, insert/update path after header
                if in_vault_section:
                    # Skip existing path line
                    if i < len(lines) and lines[i].strip().startswith("path"):
                        i += 1
                    out.append(f'path = "{path}"')
                    path_written = True
                continue
            # Replace path line within vault section
            if in_vault_section and line.startswith("path"):
                out.append(f'path = "{path}"')
                path_written = True
                i += 1
                continue
            out.append(lines[i])
            i += 1

        if not path_written:
            out.append(f'[vault]\npath = "{path}"')

        CONFIG_PATH.write_text("\n".join(out) + "\n")
    except Exception:
        pass


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
    keybindings: dict[str, str] | None = None


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
        keybindings=cfg.get("keybindings", {}),
    )
