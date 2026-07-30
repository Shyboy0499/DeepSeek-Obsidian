"""Main TUI screen with chat-primary layout, sidebar, header, and input bar."""

import re

from textual.containers import Container
from textual.screen import Screen

from deepseek_tui.engine.ai_client import Message
from deepseek_tui.tui.commands import parse_command
from deepseek_tui.tui.widgets.chat import ChatView
from deepseek_tui.tui.widgets.diff_view import DiffView
from deepseek_tui.tui.widgets.header import Header
from deepseek_tui.tui.widgets.input_bar import InputBar
from deepseek_tui.tui.widgets.sidebar import Sidebar

PROPOSAL_PATTERN = re.compile(
    r'---PROPOSE title="(?P<title>[^"]+)"\s*\n'
    r"(?P<old>.*?)\n\+\+\+\s*\n(?P<new>.*?)\n---ENDPROPOSE",
    re.DOTALL,
)


def _parse_proposals(text: str) -> list[dict]:
    """Extract edit proposals from AI response text."""
    proposals = []
    for match in PROPOSAL_PATTERN.finditer(text):
        proposals.append({
            "title": match.group("title"),
            "old": match.group("old"),
            "new": match.group("new"),
        })
    return proposals


def _clean_response(text: str) -> str:
    """Remove proposal markup from displayed response text."""
    return PROPOSAL_PATTERN.sub("", text).strip()


class MainScreen(Screen):
    """Primary screen layout."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._sidebar_visible = True

    def compose(self):
        yield Header()
        with Container(id="main-layout"):
            with Container(id="chat-column"):
                yield ChatView()
            with Container(id="sidebar-column"):
                yield Sidebar()
        yield InputBar()

    def on_mount(self) -> None:
        self._update_header()

    def _update_header(self) -> None:
        header = self.query_one(Header)
        header.posture = self._app.permissions.level.value.title()
        if self._app.vault:
            header.vault_name = self._app.vault.vault_path.name

    def update_posture(self, posture: str) -> None:
        header = self.query_one(Header)
        header.posture = posture.title()

    def focus_sidebar(self) -> None:
        self.query_one(Sidebar).focus()

    def focus_chat(self) -> None:
        self.query_one("#chat-input").focus()

    def focus_search(self) -> None:
        self.query_one("#search-input").focus()

    def toggle_sidebar(self) -> None:
        sidebar_col = self.query_one("#sidebar-column", Container)
        self._sidebar_visible = not self._sidebar_visible
        sidebar_col.display = True if self._sidebar_visible else False

    @property
    def chat_view(self) -> ChatView:
        return self.query_one(ChatView)

    @property
    def sidebar(self) -> Sidebar:
        return self.query_one(Sidebar)

    def on_input_submitted(self, event) -> None:
        """Handle Enter in the chat input."""
        if event.input.id != "chat-input":
            return
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        cmd_name, cmd_args = parse_command(text)

        if cmd_name:
            self._handle_command(cmd_name, cmd_args, text)
        else:
            self.chat_view.add_user_message(text)
            if self._app.context_builder and self._app.ai_client:
                import asyncio

                asyncio.create_task(self._send_to_ai(text))

    def _handle_command(self, cmd_name: str, cmd_args: str, raw_text: str) -> None:
        """Execute a slash command and show the result in chat."""
        try:
            result = self._app._command_registry.execute(cmd_name, cmd_args)
            if result is None:
                return
            if isinstance(result, str):
                self.chat_view.add_user_message(raw_text)
                self.chat_view.start_assistant_message()
                self.chat_view.stream_chunk(result)
                self.chat_view.finish_assistant_message()
        except ValueError as e:
            self.chat_view.add_user_message(raw_text)
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk(f"[red]{e}[/red]")
            self.chat_view.finish_assistant_message()

    async def _send_to_ai(self, text: str) -> None:
        """Send user message to AI and stream the response."""
        if not self._app.context_builder or not self._app.ai_client:
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk("No vault or AI client configured.")
            self.chat_view.finish_assistant_message()
            return

        messages, context_notes = self._app.context_builder.build(
            text,
            permission_level=self._app.permissions.level.value,
        )

        notes_data = [(n.title, str(n.path)) for n in context_notes]
        self.sidebar.notes_panel.set_notes(notes_data)

        self.chat_view.start_assistant_message()
        self.chat_view.stream_chunk("[dim]🤔 Thinking...[/dim]\n")
        full_response = ""
        try:
            async for chunk in self._app.ai_client.stream(messages):
                if chunk.content:
                    full_response += chunk.content
                    self.chat_view.stream_chunk(chunk.content)
        except Exception as e:
            error_msg = f"[red]Error: {e}[/red]"
            full_response = error_msg
            self.chat_view.stream_chunk(f"\n{error_msg}")
        self.chat_view.finish_assistant_message()

        self._app.context_builder.history.add(Message(role="user", content=text))
        self._app.context_builder.history.add(
            Message(role="assistant", content=full_response)
        )

        # Parse and mount any edit proposals as DiffView widgets
        proposals = _parse_proposals(full_response)
        for prop in proposals:
            self._mount_proposal(prop["title"], prop["old"], prop["new"])

    def _mount_proposal(
        self, note_title: str, old_text: str, new_text: str
    ) -> None:
        """Mount a DiffView for an edit proposal, wired to actually write changes."""
        vault = self._app.vault
        if not vault:
            return

        note = vault.resolve_wikilink(note_title)
        if not note:
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk(
                f'[red]Cannot apply: note "{note_title}" not found.[/red]'
            )
            self.chat_view.finish_assistant_message()
            return

        def do_accept() -> None:
            if old_text not in note.content:
                self.chat_view.start_assistant_message()
                self.chat_view.stream_chunk(
                    f'[red]Edit failed: text not found in "{note_title}".[/red]'
                )
                self.chat_view.finish_assistant_message()
                return
            previous = note.content
            updated = note.content.replace(old_text, new_text, 1)
            note.path.write_text(updated)
            self._app.permissions.audit_trail.record(
                "write", str(note.path),
                f"Applied edit to {note_title}",
                previous_content=previous,
            )
            vault.refresh()
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk(
                f'✅ Edit applied to "{note_title}".'
            )
            self.chat_view.finish_assistant_message()

        def do_reject() -> None:
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk(
                f'[dim]Edit to "{note_title}" rejected.[/dim]'
            )
            self.chat_view.finish_assistant_message()

        self.chat_view.mount(DiffView(
            note_title=note_title,
            old_text=old_text,
            new_text=new_text,
            on_accept=do_accept,
            on_reject=do_reject,
        ))
