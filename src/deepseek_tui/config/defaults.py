"""Default configuration values."""

from typing import Any

DEFAULTS: dict[str, dict[str, Any]] = {
    "vault": {
        "path": None,
        "exclude_dirs": [".git", "_templates", ".trash"],
    },
    "model": {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
    },
    "context": {
        "max_notes": 10,
        "note_preview_chars": 500,
        "full_text_search": True,
        "incremental_index": True,
    },
    "tui": {
        "theme": "",  # empty = terminal-native colors
        "permission_default": "ask",
        "sidebar_width": 35,
    },
}
