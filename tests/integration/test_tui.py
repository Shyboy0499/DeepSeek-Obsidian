"""TUI integration tests — drive the real app via Textual's test harness.

These launch DeepSeekTuiApp with a temp vault and exercise the actual UI:
commands, permissions, undo, chat, and the command palette. They catch
bugs that unit tests (which bypass the TUI) miss.
"""

import tempfile
from pathlib import Path

import pytest

from deepseek_obsidian.app import DeepSeekTuiApp
from deepseek_obsidian.engine.permissions import PermissionLevel


@pytest.fixture
def vault_dir():
    """A temp Obsidian vault with a few interlinked notes."""
    with tempfile.TemporaryDirectory() as tmp:
        v = Path(tmp)
        (v / ".obsidian").mkdir()
        (v / "ml.md").write_text(
            "---\ntitle: Machine Learning\ntags: [ml]\n---\n"
            "# Machine Learning\n\nSupervised learning and neural networks."
        )
        (v / "cooking.md").write_text("# Cooking\n\nHow to bake bread.")
        (v / "linked.md").write_text("See [[machine learning]] for more.")
        yield v


async def _make_app(vault_dir: Path) -> DeepSeekTuiApp:
    app = DeepSeekTuiApp(cli_vault=str(vault_dir))
    return app


class TestAppLaunch:
    async def test_app_mounts(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            assert "MainScreen" in [type(s).__name__ for s in app.screen_stack]

    async def test_commands_registered(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            commands = {c.name for c in app._command_registry.list_commands()}
            assert "search" in commands
            assert "read" in commands
            assert "graph" in commands
            assert "suggest-links" in commands
            assert len(commands) >= 20


class TestReadCommands:
    async def test_stats(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            out = app._cmd_stats("")
            assert "Notes: 3" in out
            assert "Wikilinks: 1" in out

    async def test_tags(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            out = app._cmd_tags("")
            assert "ml" in out

    async def test_search(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            out = app._cmd_search("neural")
            assert "Found" in out

    async def test_suggest_links(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            out = app._cmd_suggest_links("Machine Learning")
            assert "linked" in out.lower()


class TestWriteCommands:
    async def test_permission_gate(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            # Default is "ask" (read-only)
            out = app._cmd_new("blocked")
            assert "Cannot create" in out

    async def test_create_tag_delete_undo(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.permissions.set_level(PermissionLevel.FULL_ACCESS)

            assert "Created" in app._cmd_new("My Note")
            assert "Added tag" in app._cmd_tag("add cooking important")
            assert "Deleted" in app._cmd_delete("My Note")

            # Undo the delete — note should be recreated
            app.action_undo()
            titles = {n.title for n in app.vault.notes}
            assert "My Note" in titles


class TestTUIInteraction:
    async def test_input_submission_renders_in_chat(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from textual.widgets import Input
            screen = app.screen_stack[-1]
            chat_input = screen.query_one("#chat-input", Input)
            chat_input.value = "/stats"
            chat_input.post_message(Input.Submitted(chat_input, "/stats"))
            await pilot.pause()

            texts = [c.text for c in screen.chat_view.children if hasattr(c, "text")]
            assert any("Vault statistics" in t for t in texts)

    async def test_ctrl_p_opens_palette(self, vault_dir):
        app = await _make_app(vault_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.press("ctrl+p")
            await pilot.pause()
            assert "CommandPalette" in [type(s).__name__ for s in app.screen_stack]
