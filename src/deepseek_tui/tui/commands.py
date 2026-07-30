"""Slash command system — register, parse, and execute commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


def parse_command(text: str) -> tuple[str | None, str]:
    """Parse a slash command from input text.
    Returns: (command_name, args) if starts with '/', else (None, raw_text).
    """
    text = text.strip()
    if not text.startswith("/"):
        return None, text

    parts = text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


@dataclass
class Command:
    name: str
    description: str
    handler: Callable[[str], Any]


class CommandRegistry:
    """Registry for slash commands."""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def list_commands(self) -> list[Command]:
        return list(self._commands.values())

    def execute(self, name: str, args: str) -> Any:
        cmd = self.get(name)
        if cmd is None:
            raise ValueError(f"Unknown command: {name}")
        return cmd.handler(args)
