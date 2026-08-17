"""Application entry point — wires engine to TUI."""

from __future__ import annotations

import os
from pathlib import Path

from textual.app import App

from deepseek_obsidian.config.loader import (
    load_config,
    save_model_config,
    save_vault_path,
)
from deepseek_obsidian.engine.ai_client import AIClient, create_client
from deepseek_obsidian.engine.context import ContextBuilder
from deepseek_obsidian.engine.permissions import PermissionLevel, Permissions
from deepseek_obsidian.engine.vault import VaultReader
from deepseek_obsidian.tui.screen import MainScreen


class DeepSeekTuiApp(App):
    """Main TUI application."""

    CSS = """
    MainScreen {
        layout: grid;
        grid-size: 1;
    }

    #main-layout {
        layout: horizontal;
        height: 1fr;
    }

    #chat-column {
        width: 1fr;
    }

    #sidebar-column {
        width: 35;
    }

    Header {
        dock: top;
        height: 1;
        padding: 0 1;
    }

    #header-title {
        width: 1fr;
    }

    #header-posture {
        width: auto;
        padding: 0 1;
        text-style: bold;
    }

    #header-vault {
        width: auto;
        padding: 0 1;
    }

    InputBar {
        dock: bottom;
        height: auto;
        padding: 0 1;
    }

    #input-row {
        height: 3;
    }

    #chat-input {
        width: 1fr;
    }

    ChatView {
        height: 1fr;
    }

    Sidebar {
        height: 1fr;
    }

    ReferencedNotesPanel {
        height: 1fr;
    }

    SearchPanel {
        height: auto;
    }

    .panel-title {
        padding: 0 1;
        text-style: bold;
    }
    """

    def __init__(self, cli_vault: str | None = None):
        super().__init__()
        self.config = load_config()
        self.BINDINGS = self._build_bindings()  # type: ignore
        self.permissions = Permissions(
            level=PermissionLevel.from_string(self.config.permission_default)
        )
        self._vaults: list[VaultReader] = []
        self.ai_client: AIClient | None = None
        self.context_builder: ContextBuilder | None = None
        self._cli_vault = cli_vault
        self._vault_candidates: list[Path] = []
        self._detect_terminal_theme()

    @property
    def vault(self) -> VaultReader | None:
        """Primary vault (first loaded)."""
        return self._vaults[0] if self._vaults else None

    @property
    def vaults(self) -> list[VaultReader]:
        return self._vaults

    def _build_bindings(self) -> list[tuple[str, str, str]]:
        kb = self.config.keybindings or {}
        labels = {
            "cycle_permission": "Cycle Permission",
            "focus_sidebar": "Focus Sidebar",
            "focus_chat": "Focus Chat",
            "quick_search": "Quick Search",
            "toggle_sidebar": "Toggle Sidebar",
            "undo": "Undo",
            "quit": "Quit",
        }
        defaults = [
            ("cycle_permission", "tab"),
            ("focus_sidebar", "ctrl+n"),
            ("focus_chat", "ctrl+l"),
            ("quick_search", "ctrl+s"),
            ("toggle_sidebar", "ctrl+b"),
            ("undo", "ctrl+z"),
            ("quit", "ctrl+q"),
        ]
        return [(kb.get(k, d), k, labels[k]) for k, d in defaults]

    def on_mount(self) -> None:
        self._command_registry = self._build_command_registry()
        self.push_screen(MainScreen(self))

        if self.ai_client is None:
            self.ai_client = create_client(
                self.config.provider,
                self.config.model,
                api_key=self.config.api_key,
            )

        self.call_after_refresh(self._detect_and_load_vault)

    def _detect_and_load_vault(self) -> None:
        if self._cli_vault:
            self._load_vault(Path(self._cli_vault).expanduser())
            return

        if self.config.vault_path and self.config.vault_path.exists():
            self._load_vault(self.config.vault_path)
            return

        candidates = self._find_vaults()
        if len(candidates) == 0:
            self._show_setup_guide()
        elif len(candidates) == 1:
            self._load_vault(candidates[0])
        else:
            lines = [
                f"Found {len(candidates)} vaults. "
                "Use /vault with a number to pick one:"
            ]
            self._vault_candidates = candidates
            for i, path in enumerate(candidates, 1):
                lines.append(f"  [{i}] {path}")
            self._notify("\n".join(lines))

    def _show_setup_guide(self) -> None:
        no_key = not self.config.api_key
        provider = self.config.provider.upper()
        guide = ["Welcome to DeepSeek-Obsidian! 🚀", ""]
        guide.append("To get started:")
        guide.append(
            f"  1. Set your API key: export {provider}_API_KEY=\"sk-...\""
        )
        guide.append("  2. Connect a vault: /vault /path/to/vault")
        guide.append("  3. Try: /search to find notes, then ask the AI")
        guide.append("")
        if no_key:
            guide.append(
                f"⚠️  No {provider}_API_KEY set — AI won't respond."
            )
        guide.append("Type /help for all commands.")
        self._notify("\n".join(guide))

    def _find_vaults(self) -> list[Path]:
        search_dirs = [
            Path.home() / "Documents",
            Path.home() / "Obsidian",
            Path.home() / "Desktop",
        ]
        candidates: list[Path] = []
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            # Direct child — most vaults are one level deep
            for child in search_dir.iterdir():
                if child.is_dir() and (child / ".obsidian").exists():
                    if child not in candidates:
                        candidates.append(child)
            # Also check search_dir itself
            if (search_dir / ".obsidian").exists():
                if search_dir not in candidates:
                    candidates.append(search_dir)
        return candidates

    def _detect_terminal_theme(self) -> None:
        """Set theme based on terminal background color.
        Uses $COLORFGBG (common in most terminals): format "fg;bg".
        0-7 = dark, 8-15 = light.
        """
        colorfgbg = os.environ.get("COLORFGBG", "")
        try:
            _, bg = colorfgbg.split(";")
            bg_val = int(bg)
        except (ValueError, IndexError):
            bg_val = 0  # default: assume dark

        if bg_val >= 7:
            self.theme = "textual-light"

    def _notify(self, message: str, severity: str = "information") -> None:
        """Show a toast notification (preferred) or fall back to chat message."""
        try:
            self.notify(message, severity=severity)  # type: ignore[arg-type]
        except Exception:
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.chat_view.start_assistant_message()
                screen.chat_view.stream_chunk(f"⚙️ {message}")
                screen.chat_view.finish_assistant_message()

    def _load_vault(self, path: Path, add: bool = False) -> None:
        def _on_vault_change() -> None:
            self._notify("📁 Vault changed — index refreshed.")

        if not add:
            for v in self._vaults:
                v.stop_watcher()
            self._vaults.clear()

        vault = VaultReader(
            path,
            exclude_dirs=self.config.exclude_dirs,
            on_change=_on_vault_change,
        )
        self._vaults.append(vault)
        if not add:
            save_vault_path(str(path))
            session_path = (
                Path.home() / ".config" / "deepseek-obsidian" / "sessions"
                / f"{vault.vault_path.name}.json"
            )
            self.context_builder = ContextBuilder(
                vault, max_notes=self.config.max_notes,
                session_path=session_path,
            )
            if self.config.incremental_index:
                import asyncio
                asyncio.create_task(vault.start_watcher())
        total = sum(len(v.notes) for v in self._vaults)
        if add:
            self._notify(
                f"📁 Added vault: {path.name} ({len(vault.notes)} notes). "
                f"Total: {len(self._vaults)} vaults, {total} notes."
            )
            return
        lines = [
            f"📁 Vault connected: {path.name} ({len(vault.notes)} notes)",
        ]
        if self.context_builder and self.context_builder.restored_count:
            lines.append(
                f"💬 Restored {self.context_builder.restored_count} "
                f"messages from last session"
            )
        if not self.config.api_key:
            provider = self.config.provider.upper()
            lines.append(
                f"⚠️  No {provider}_API_KEY set — AI chat won't work. "
                f"Export your key and restart."
            )
        lines.append(
            "Try /search to find notes, /help for all commands."
        )
        self._notify("\n".join(lines))

    def action_cycle_permission(self) -> None:
        new_level = self.permissions.cycle()
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.update_posture(new_level.value)

    def action_focus_sidebar(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_sidebar()

    def action_focus_chat(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_chat()

    def action_quick_search(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.focus_search()

    def action_toggle_sidebar(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.toggle_sidebar()

    def action_undo(self) -> None:
        entry = self.permissions.audit_trail.pop_last_write()
        if entry is None:
            self._notify("Nothing to undo.")
            return

        target = Path(entry.target)
        if entry.previous_content == "__NEW_FILE__":
            # Undo a file creation — delete the file
            if target.exists():
                target.unlink()
                self._notify(f"Undo: deleted {target.name}")
        elif entry.detail.startswith("Deleted"):
            # Undo a deletion — recreate the file (content may be empty)
            target.write_text(entry.previous_content)
            self._notify(f"Undo: restored deleted note {target.name}")
        elif entry.previous_content:
            # Undo a modification — restore previous content
            target.write_text(entry.previous_content)
            self._notify(f"Undo: restored {target.name}")
        else:
            self._notify(f"Cannot undo: no previous state saved for {target.name}")

        # Persist the updated audit trail
        self.permissions._save_audit()

        # Refresh vault if loaded
        if self.vault:
            self.vault.refresh()

    def _build_command_registry(self):
        from deepseek_obsidian.tui.commands import Command, CommandRegistry

        registry = CommandRegistry()

        registry.register(Command(
            name="model", description="Switch AI provider/model",
            handler=self._cmd_model,
        ))
        registry.register(Command(
            name="search", description="Search the vault",
            handler=self._cmd_search,
        ))
        registry.register(Command(
            name="open", description="Open a note by wikilink",
            handler=self._cmd_open,
        ))
        registry.register(Command(
            name="save", description="Save last AI response as a note",
            handler=self._cmd_save,
        ))
        registry.register(Command(
            name="link", description="Create a wikilink between notes",
            handler=self._cmd_link,
        ))
        registry.register(Command(
            name="new", description="Create a new note",
            handler=self._cmd_new,
        ))
        registry.register(Command(
            name="backlinks", description="Show notes linking to a note",
            handler=self._cmd_backlinks,
        ))
        registry.register(Command(
            name="graph", description="Visualize note connections",
            handler=self._cmd_graph,
        ))
        registry.register(Command(
            name="config", description="Edit settings interactively",
            handler=self._cmd_config,
        ))
        registry.register(Command(
            name="read", description="Read a full note",
            handler=self._cmd_read,
        ))
        registry.register(Command(
            name="edit", description="Edit a note in your editor",
            handler=self._cmd_edit,
        ))
        registry.register(Command(
            name="delete", description="Delete a note",
            handler=self._cmd_delete,
        ))
        registry.register(Command(
            name="today", description="Open today's daily note",
            handler=self._cmd_today,
        ))
        registry.register(Command(
            name="tag", description="Add/remove tags on a note",
            handler=self._cmd_tag,
        ))
        registry.register(Command(
            name="stats", description="Vault health statistics",
            handler=self._cmd_stats,
        ))
        registry.register(Command(
            name="tags", description="List tags or filter by tag",
            handler=self._cmd_tags,
        ))
        registry.register(Command(
            name="vault", description="Switch to a different vault",
            handler=self._cmd_vault,
        ))
        registry.register(Command(
            name="export", description="Export chat to markdown",
            handler=self._cmd_export,
        ))
        registry.register(Command(
            name="clear", description="Clear current chat",
            handler=self._cmd_clear,
        ))
        registry.register(Command(
            name="theme", description="Switch TUI theme",
            handler=self._cmd_theme,
        ))
        registry.register(Command(
            name="perm", description="Set permission posture",
            handler=self._cmd_perm,
        ))
        registry.register(Command(
            name="help", description="Show available commands",
            handler=self._cmd_help,
        ))
        return registry

    def _cmd_model(self, args: str) -> str:
        if not args.strip():
            provider = self.ai_client.provider if self.ai_client else self.config.provider
            return (
                f"Current: {provider}. "
                "Usage: /model <provider> [model]\n"
                "Providers: deepseek, anthropic, openai, ollama"
            )

        parts = args.split()
        provider_name = parts[0]
        model = parts[1] if len(parts) > 1 else None

        try:
            from deepseek_obsidian.engine.ai_client import AIProvider
            prov = AIProvider.from_string(provider_name)
            chosen_model = model or prov.default_model
            self.ai_client = create_client(
                provider_name, chosen_model,
                api_key=self.config.api_key,
            )
            self.config.provider = provider_name
            self.config.model = chosen_model
            save_model_config(provider_name, chosen_model)
            return (
                f"Requested: {provider_name}/{chosen_model} (saved)\n"
                "Actual model confirmed on next message."
            )
        except ValueError:
            return (
                f"Unknown provider: {provider_name}. "
                "Available: deepseek, anthropic, openai, ollama"
            )

    def _cmd_search(self, args: str) -> str:
        if not self._vaults:
            return "No vault loaded."

        tag_filter = ""
        from_date = ""
        to_date = ""
        semantic = False
        query = args

        # Parse flags: --tag, --from, --to, --semantic
        parts = args.split()
        i = 0
        query_parts = []
        while i < len(parts):
            if parts[i] == "--tag" and i + 1 < len(parts):
                tag_filter = parts[i + 1]
                i += 2
            elif parts[i] == "--from" and i + 1 < len(parts):
                from_date = parts[i + 1]
                i += 2
            elif parts[i] == "--to" and i + 1 < len(parts):
                to_date = parts[i + 1]
                i += 2
            elif parts[i] == "--semantic":
                semantic = True
                i += 1
            else:
                query_parts.append(parts[i])
                i += 1
        query = " ".join(query_parts)

        # Start with results (first vault)
        primary = self._vaults[0]
        if query:
            if semantic:
                results = primary.search_semantic(query)
            else:
                results = primary.search_full_text(query)
        else:
            results = list(primary.notes)

        # Search across all additional vaults too
        for v in self._vaults[1:]:
            if query:
                if semantic:
                    results.extend(v.search_semantic(query))
                else:
                    results.extend(v.search_full_text(query))
            else:
                results.extend(v.notes)

        # Filter by tag
        if tag_filter:
            results = [n for n in results if tag_filter in n.tags]

        # Filter by date range (title contains date-like patterns)
        if from_date:
            results = [n for n in results if n.title >= from_date]
        if to_date:
            results = [n for n in results if n.title <= to_date]

        screen = self.screen
        if isinstance(screen, MainScreen):
            notes_data = [(n.title, str(n.path)) for n in results[:20]]
            screen.sidebar.search_panel.set_results(notes_data)

        filters = []
        if tag_filter:
            filters.append(f"tag={tag_filter}")
        if from_date:
            filters.append(f"from={from_date}")
        if to_date:
            filters.append(f"to={to_date}")
        filter_str = f" ({', '.join(filters)})" if filters else ""
        q_str = f"'{query}'" if query else "all notes"
        return f"Found {len(results)} notes matching {q_str}{filter_str}."

    def _cmd_open(self, args: str) -> str:
        if not self.vault or not args:
            return "No vault loaded. Use /vault <path> to open a vault first."
        link = args.strip().strip("[[").strip("]]")
        note = self.vault.resolve_wikilink(link)
        if note:
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.sidebar.notes_panel.set_notes([(note.title, str(note.path))])
            return f"Opened: {note.title}"
        return f"Note not found: \"{link}\" — use /search to find notes by keyword"

    def _cmd_save(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        if not self.permissions.can_write():
            return (
                "Cannot save: permission is 'Ask' (read-only). "
                "Press Tab to cycle to Full Access, or use /perm full."
            )
        screen = self.screen
        if isinstance(screen, MainScreen):
            chat_view = screen.chat_view
            # Get the last assistant message content from the chat view children
            for child in reversed(list(chat_view.children)):
                from deepseek_obsidian.tui.widgets.chat import ChatMessage
                if isinstance(child, ChatMessage) and child.role == "assistant":
                    content = child.text
                    break
            else:
                return "No AI response to save. Send a message to the AI first."
        else:
            return "No AI response to save. Send a message to the AI first."
        filename = args.strip() if args.strip() else "untitled.md"
        filepath = self.vault.vault_path / filename
        filepath.write_text(str(content))
        self.permissions.record_write(
            str(filepath), "Created note from AI response",
            previous_content="__NEW_FILE__",
        )
        self.vault.refresh()
        return f"Saved to {filename}"

    def _cmd_link(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        if "->" not in args:
            return "Usage: /link <from> -> <to>"
        from_note, to_note = args.split("->", 1)
        from_note = from_note.strip()
        to_note = to_note.strip()
        if not self.permissions.can_write():
            return f"Would link [[{from_note}]] -> [[{to_note}]] (Full Access required)."
        note = self.vault.resolve_wikilink(from_note)
        if note:
            prev = note.content
            content = prev + f"\n\nSee also: [[{to_note}]]"
            note.path.write_text(content)
            self.permissions.record_write(
                str(note.path),
                f"Added link to [[{to_note}]]",
                previous_content=prev,
            )
            self.vault.refresh()
            return f"Linked [[{from_note}]] -> [[{to_note}]]"
        return f"Note not found: \"{from_note}\" — check the title with /search"

    def _cmd_new(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        if not self.permissions.can_write():
            return (
                "Cannot create: permission is 'Ask' (read-only). "
                "Press Tab to cycle to Full Access, or use /perm full."
            )
        title = args.strip() or "untitled"
        filename = f"{title}.md"
        filepath = self.vault.vault_path / filename
        if filepath.exists():
            return f"Note already exists: {filename}"
        content = f"# {title}\n\n"
        filepath.write_text(content)
        self.permissions.record_write(
            str(filepath), f"Created note: {title}",
            previous_content="__NEW_FILE__",
        )
        self.vault.refresh()
        return f"Created: [[{title}]]"

    def _cmd_edit(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded."
        title = args.strip().strip("[[").strip("]]")
        if not title:
            return "Usage: /edit Note Title"
        note = self.vault.resolve_wikilink(title)
        if not note:
            return f"Note not found: \"{title}\""
        if not self.permissions.can_write():
            return (
                "Cannot edit: permission is 'Ask'. "
                "Use /perm full or press Tab to cycle."
            )
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vim"))
        import subprocess
        previous = note.content
        result = subprocess.run([editor, str(note.path)])
        if result.returncode != 0:
            return f"Editor exited with code {result.returncode}."
        new_content = note.path.read_text(encoding="utf-8")
        if new_content != previous:
            self.permissions.record_write(
                str(note.path), f"Manual edit: {title}",
                previous_content=previous,
            )
            self.vault.refresh()
            return f"Edited: [[{title}]]"
        return f"No changes to {title}."

    def _cmd_delete(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded."
        title = args.strip().strip("[[").strip("]]")
        if not title:
            return "Usage: /delete Note Title"
        note = self.vault.resolve_wikilink(title)
        if not note:
            return f"Note not found: \"{title}\""
        if not self.permissions.can_write():
            return (
                "Cannot delete: permission is 'Ask'. "
                "Use /perm full or press Tab to cycle."
            )
        previous = note.content
        note.path.unlink()
        self.permissions.record_write(
            str(note.path), f"Deleted note: {title}",
            previous_content=previous,
        )
        self.vault.refresh()
        return f"Deleted: {title} (undo with Ctrl+Z)"

    def _cmd_today(self, args: str) -> str | None:
        if not self.vault:
            return "No vault loaded."
        import datetime
        today = datetime.date.today().isoformat()
        filename = f"{today}.md"
        filepath = self.vault.vault_path / filename
        if not filepath.exists():
            if not self.permissions.can_write():
                return (
                    "Cannot create daily note: permission is 'Ask'. "
                    "Use /perm full."
                )
            filepath.write_text(f"# {today}\n\n")
            self.permissions.record_write(
                str(filepath), f"Created daily note: {today}",
                previous_content="__NEW_FILE__",
            )
            self.vault.refresh()
        note = self.vault.resolve_wikilink(today)
        if note:
            from deepseek_obsidian.tui.screens.reader import NoteReaderScreen
            self.push_screen(NoteReaderScreen(note))
        return None

    def _cmd_tag(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded."
        parts = args.split()
        if len(parts) < 3:
            return "Usage: /tag add|remove <NoteTitle> <tag>"
        action = parts[0].lower()
        tag = parts[-1]
        title = " ".join(parts[1:-1]).strip().strip("[[").strip("]]")
        if action not in ("add", "remove"):
            return "Usage: /tag add|remove <NoteTitle> <tag>"
        note = self.vault.resolve_wikilink(title)
        if not note:
            return f"Note not found: \"{title}\""
        if not self.permissions.can_write():
            return (
                "Cannot modify tags: permission is 'Ask'. "
                "Use /perm full or press Tab."
            )
        from deepseek_obsidian.engine.vault import update_tags
        previous = note.content
        if action == "add":
            update_tags(note, add=[tag])
        else:
            update_tags(note, remove=[tag])
        self.permissions.record_write(
            str(note.path), f"{action} tag '{tag}' on {title}",
            previous_content=previous,
        )
        self.vault.refresh()
        return f"{action.capitalize()}ed tag '{tag}' on [[{title}]]"

    def _cmd_stats(self, args: str) -> str:
        if not self._vaults:
            return "No vault loaded."
        lines = []
        total_notes = 0
        total_links = 0
        broken = 0
        all_tags: set[str] = set()
        for v in self._vaults:
            total_notes += len(v.notes)
            for n in v.notes:
                links = n.wikilinks()
                total_links += len(links)
                for link in links:
                    if v.resolve_wikilink(link) is None:
                        broken += 1
                all_tags.update(n.tags)
        lines.append(f"📊 Vault statistics ({len(self._vaults)} vault(s))")
        lines.append(f"  Notes: {total_notes}")
        lines.append(f"  Wikilinks: {total_links}")
        lines.append(f"  Broken links: {broken}")
        lines.append(f"  Tags: {len(all_tags)}")
        # Most-linked notes
        from deepseek_obsidian.engine.graph import build_graph
        for v in self._vaults:
            graph = build_graph(v)
            top = sorted(
                graph.nodes.values(), key=lambda node: -node.degree
            )[:5]
            if top:
                lines.append("  Most connected notes:")
                for node in top:
                    if node.degree > 0:
                        lines.append(
                            f"    • [[{node.title}]] ({node.degree})"
                        )
        return "\n".join(lines)

    def _cmd_tags(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded."
        tag_filter = args.strip()
        if tag_filter:
            matches = [n for n in self.vault.notes if tag_filter in n.tags]
            if not matches:
                return f"No notes with tag \"{tag_filter}\"."
            result = f"Notes tagged \"{tag_filter}\" ({len(matches)}):"
            for n in matches[:20]:
                result += f"\n  • [[{n.title}]]"
            return result
        # List all tags
        all_tags: dict[str, int] = {}
        for n in self.vault.notes:
            for t in n.tags:
                all_tags[t] = all_tags.get(t, 0) + 1
        if not all_tags:
            return "No tags found in vault. Add frontmatter tags to notes."
        result = f"Tags ({len(all_tags)}):"
        for tag, count in sorted(all_tags.items()):
            result += f"\n  {tag} ({count})"
        return result

    def _cmd_read(self, args: str) -> str | None:
        if not self._vaults:
            return "No vault loaded."
        title = args.strip().strip("[[").strip("]]")
        if not title:
            return "Usage: /read Note Title"
        for vault in self._vaults:
            note = vault.resolve_wikilink(title)
            if note:
                from deepseek_obsidian.tui.screens.reader import NoteReaderScreen
                self.push_screen(NoteReaderScreen(note))
                return None
        return f"Note not found: \"{title}\""

    def _cmd_config(self, args: str) -> str | None:
        from deepseek_obsidian.tui.screens.config import ConfigScreen
        self.push_screen(ConfigScreen(self.config))
        return None

    def _cmd_graph(self, args: str) -> str | None:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        from deepseek_obsidian.tui.screens.graph import GraphScreen
        self.push_screen(GraphScreen(self.vault))
        return None

    def _cmd_backlinks(self, args: str) -> str:
        if not self.vault:
            return "No vault loaded. Use /vault <path> to open one."
        title = args.strip().strip("[[").strip("]]")
        if not title:
            return "Usage: /backlinks [[Note Title]] or /backlinks Note Title"
        backlinks = self.vault.backlinks(title)
        if not backlinks:
            return f"No notes link to \"{title}\"."
        result = f"{len(backlinks)} note(s) link to [[{title}]]:"
        for n in backlinks:
            result += f"\n  • [[{n.title}]]"
        return result

    def _cmd_vault(self, args: str) -> str:
        arg = args.strip()

        # List loaded vaults
        if arg == "list" or arg == "":
            if not self._vaults:
                return "No vaults loaded. Use /vault <path> to open one."
            result = f"{len(self._vaults)} vault(s) loaded:"
            for i, v in enumerate(self._vaults, 1):
                result += f"\n  [{i}] {v.vault_path.name} ({len(v.notes)} notes)"
            return result

        # Add a vault
        if arg.startswith("add "):
            path = Path(arg[4:].strip()).expanduser()
            if path.exists() and (path / ".obsidian").exists():
                self._load_vault(path, add=True)
                return f"Added vault: {path.name}"
            return f"Not a valid Obsidian vault: {path}"

        # Try numeric index into candidates list
        if arg.isdigit() and self._vault_candidates:
            idx = int(arg) - 1
            if 0 <= idx < len(self._vault_candidates):
                path = self._vault_candidates[idx]
                self._load_vault(path)
                self._vault_candidates = []
                screen = self.screen
                if isinstance(screen, MainScreen):
                    screen._update_header()
                return f"Switched to vault: {path.name}"
            return f"Invalid vault number. Choose 1-{len(self._vault_candidates)}."

        path = Path(arg).expanduser()
        if path.exists() and (path / ".obsidian").exists():
            self._load_vault(path)
            self._vault_candidates = []
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen._update_header()
            return f"Switched to vault: {path.name}"
        return f"Not a valid Obsidian vault (no .obsidian/ folder): {path}"

    def _cmd_export(self, args: str) -> str:
        import json
        fmt = "md"
        output = args.strip()
        if output.startswith("--json"):
            fmt = "json"
            output = output.removeprefix("--json").strip()
        path = (
            Path(output).expanduser() if output
            else Path.home() / f"deepseek-obsidian-export.{fmt}"
        )
        screen = self.screen
        if isinstance(screen, MainScreen):
            from deepseek_obsidian.tui.widgets.chat import ChatMessage
            messages = []
            for child in screen.chat_view.children:
                if isinstance(child, ChatMessage):
                    messages.append({"role": child.role, "content": child.text})
            if not messages:
                return "Nothing to export."
            if fmt == "json":
                path.write_text(json.dumps(messages, indent=2))
            else:
                md_lines = [f"## {m['role']}\n\n{m['content']}\n" for m in messages]
                path.write_text("\n---\n".join(md_lines))
            return f"Exported {len(messages)} messages to {path}"
        return "Nothing to export. Chat with the AI first, then use /export."

    def _cmd_clear(self, args: str) -> str:
        screen = self.screen
        if isinstance(screen, MainScreen):
            if args.strip() == "--save":
                self._cmd_export("")
            screen.chat_view.clear_chat()
            if self.context_builder:
                self.context_builder.history.clear()
            return "Chat cleared."
        return "OK"

    def _cmd_theme(self, args: str) -> str:
        theme = args.strip()
        available = [
            "dark", "light", "terminal",
            "dracula", "nord", "catppuccin", "monokai",
        ]
        if theme == "terminal" or theme == "dark":
            self.theme = "textual-dark"
            return "Theme: dark (terminal-native)."
        if theme == "light":
            self.theme = "textual-light"
            return "Theme: light."
        if theme in available:
            self.theme = theme
            return f"Theme changed to {theme}."
        return f"Available: {', '.join(available)}"

    def _cmd_perm(self, args: str) -> str:
        try:
            level = PermissionLevel.from_string(args.strip())
            self.permissions.set_level(level)
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.update_posture(level.value)
            return f"Permission set to: {level.value}"
        except ValueError:
            return "Usage: /perm ask|review|full  (or press Tab to cycle)"

    def _cmd_help(self, args: str) -> str | None:
        from deepseek_obsidian.tui.screens.help import HelpModal

        commands = [
            f"  /{cmd.name} — {cmd.description}"
            for cmd in self._command_registry.list_commands()
        ]
        keybindings = [
            "  Tab — Cycle permission posture",
            "  Ctrl+N — Focus sidebar",
            "  Ctrl+L — Focus chat",
            "  Ctrl+S — Quick vault search",
            "  Ctrl+B — Toggle sidebar",
            "  Ctrl+Z — Undo last write",
            "  Ctrl+Q — Quit",
        ]
        self.push_screen(HelpModal(commands, keybindings))
        return None


def main() -> None:
    import argparse

    from deepseek_obsidian import __version__

    parser = argparse.ArgumentParser(
        prog="deepseek-obsidian",
        description=(
            "AI-native note-taking and research assistant "
            "for the terminal with Obsidian integration."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"deepseek-obsidian {__version__}"
    )
    parser.add_argument(
        "--vault", type=str, metavar="PATH",
        help="Path to Obsidian vault (bypasses auto-detection)",
    )
    args = parser.parse_args()

    app = DeepSeekTuiApp(cli_vault=args.vault)
    app.run()


if __name__ == "__main__":
    main()
