"""Tests for slash command system."""

import pytest

from deepseek_obsidian.tui.commands import (
    Command,
    CommandRegistry,
    parse_command,
)


class TestParseCommand:
    def test_parses_slash_command(self):
        cmd, args = parse_command("/search machine learning")
        assert cmd == "search"
        assert args == "machine learning"

    def test_no_slash_returns_none(self):
        cmd, args = parse_command("hello world")
        assert cmd is None
        assert args == "hello world"

    def test_slash_with_no_args(self):
        cmd, args = parse_command("/help")
        assert cmd == "help"
        assert args == ""

    def test_slash_at_start_only(self):
        cmd, args = parse_command("use /search for searching")
        assert cmd is None
        assert args == "use /search for searching"


class TestCommandRegistry:
    def test_registers_and_finds_command(self):
        registry = CommandRegistry()
        registry.register(Command(
            name="test", description="Test command",
            handler=lambda args: "ok",
        ))
        cmd = registry.get("test")
        assert cmd is not None
        assert cmd.name == "test"

    def test_get_nonexistent_returns_none(self):
        registry = CommandRegistry()
        assert registry.get("nonexistent") is None

    def test_list_commands_returns_all(self):
        registry = CommandRegistry()
        registry.register(Command(name="a", description="A", handler=lambda a: None))
        registry.register(Command(name="b", description="B", handler=lambda a: None))
        commands = registry.list_commands()
        assert len(commands) == 2
        names = {c.name for c in commands}
        assert names == {"a", "b"}

    def test_execute_runs_handler(self):
        registry = CommandRegistry()
        results = []
        registry.register(Command(
            name="echo",
            description="Echo back",
            handler=lambda args: results.append(args),
        ))
        registry.execute("echo", "hello")
        assert results == ["hello"]

    def test_execute_unknown_raises(self):
        registry = CommandRegistry()
        with pytest.raises(ValueError, match="Unknown command"):
            registry.execute("nonexistent", "")


class TestCommand:
    def test_command_attributes(self):
        cmd = Command(
            name="search",
            description="Search the vault",
            handler=lambda args: args,
        )
        assert cmd.name == "search"
        assert cmd.description == "Search the vault"
        assert cmd.handler("test") == "test"
