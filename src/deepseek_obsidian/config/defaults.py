"""Default configuration values."""

from typing import Any

DEFAULTS: dict[str, dict[str, Any]] = {
    "vault": {
        "path": None,
        "exclude_dirs": [".git", "_templates", ".trash"],
    },
    "model": {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
    },
    "context": {
        "max_notes": 10,
        "note_preview_chars": 2000,
        "full_text_search": True,
        "incremental_index": True,
    },
    "tui": {
        "theme": "",  # empty = terminal-native colors
        "permission_default": "ask",
        "sidebar_width": 35,
    },
    "keybindings": {
        "cycle_permission": "tab",
        "focus_sidebar": "ctrl+n",
        "focus_chat": "ctrl+l",
        "quick_search": "ctrl+s",
        "toggle_sidebar": "ctrl+b",
        "undo": "ctrl+z",
        "quit": "ctrl+q",
    },
}
