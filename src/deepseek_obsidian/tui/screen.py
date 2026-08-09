"""Main TUI screen with chat-primary layout, sidebar, header, and input bar."""

import re

from textual.containers import Container
from textual.screen import Screen

from deepseek_obsidian.engine.ai_client import Message
from deepseek_obsidian.tui.commands import parse_command
from deepseek_obsidian.tui.widgets.chat import ChatView
from deepseek_obsidian.tui.widgets.diff_view import DiffView
from deepseek_obsidian.tui.widgets.header import Header
from deepseek_obsidian.tui.widgets.input_bar import InputBar
from deepseek_obsidian.tui.widgets.sidebar import Sidebar

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
        if not self._app.vault:
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk(
                "No vault loaded. Use /vault <path> to open one."
            )
            self.chat_view.finish_assistant_message()
            return

        if not self._app.config.api_key:
            self.chat_view.start_assistant_message()
            prov = self._app.config.provider.upper()
            self.chat_view.stream_chunk(
                f"No {prov}_API_KEY set. Export your key and restart deepseek-obsidian."
            )
            self.chat_view.finish_assistant_message()
            return

        model = self._app.ai_client.model if self._app.ai_client else ""
        messages, context_notes = self._app.context_builder.build(
            text,
            permission_level=self._app.permissions.level.value,
            model=model,
        )

        notes_data = [(n.title, str(n.path)) for n in context_notes]
        self.sidebar.notes_panel.set_notes(notes_data)

        self.chat_view.start_assistant_message()
        self.chat_view.stream_chunk("[dim]🤔 Thinking...[/dim]\n")
        full_response = ""
        reasoning_shown = False
        try:
            async for chunk in self._app.ai_client.stream(messages):
                if chunk.reasoning:
                    if not reasoning_shown:
                        self.chat_view.stream_chunk("[dim]")
                        reasoning_shown = True
                    self.chat_view.stream_chunk(chunk.reasoning)
                if chunk.content:
                    if reasoning_shown:
                        self.chat_view.stream_chunk("[/dim]\n")
                        reasoning_shown = False
                    full_response += chunk.content
                    self.chat_view.stream_chunk(chunk.content)
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "Unauthorized" in err_str:
                client = self._app.ai_client
                has_key = client.api_key is not None if client else False
                key_env = {
                    "deepseek": "DEEPSEEK_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY",
                    "openai": "OPENAI_API_KEY",
                }.get(client.provider.value if client else "", "API key")
                error_msg = (
                    f"[red]401 Unauthorized[/red]\n"
                    f"Provider: {client.provider.value if client else '?'}\n"
                    f"Key set: {'yes' if has_key else 'NO — export ' + key_env}"
                )
            else:
                error_msg = f"[red]Error: {err_str}[/red]"
            full_response = error_msg
            self.chat_view.stream_chunk(f"\n{error_msg}")
        self.chat_view.finish_assistant_message()

        # Show actual model the API ran (may differ from requested)
        actual = self._app.ai_client.last_actual_model if self._app.ai_client else ""
        if actual and actual != self._app.config.model:
            self.chat_view.start_assistant_message()
            self.chat_view.stream_chunk(
                f"[dim]⚙️ Requested {self._app.config.model}, "
                f"API ran {actual}[/dim]"
            )
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

        def do_accept(replacement_text: str) -> None:
            if old_text not in note.content:
                self.chat_view.start_assistant_message()
                self.chat_view.stream_chunk(
                    f'[red]Edit failed: text not found in "{note_title}".'
                    f'[/red]'
                )
                self.chat_view.finish_assistant_message()
                return
            previous = note.content
            updated = note.content.replace(old_text, replacement_text, 1)
            note.path.write_text(updated)
            self._app.permissions.record_write(
                str(note.path),
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
