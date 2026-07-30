"""Main TUI screen with chat-primary layout, sidebar, header, and input bar."""

from textual.containers import Container
from textual.screen import Screen

from deepseek_tui.engine.ai_client import Message
from deepseek_tui.tui.commands import parse_command
from deepseek_tui.tui.widgets.chat import ChatView
from deepseek_tui.tui.widgets.header import Header
from deepseek_tui.tui.widgets.input_bar import InputBar
from deepseek_tui.tui.widgets.sidebar import Sidebar


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
        self.chat_view.add_user_message(raw_text)
        try:
            result = self._app._command_registry.execute(cmd_name, cmd_args)
            if isinstance(result, str):
                self.chat_view.start_assistant_message()
                self.chat_view.stream_chunk(result)
                self.chat_view.finish_assistant_message()
        except ValueError as e:
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
        self.chat_view.stream_chunk("[dim]🤔 Thinking...[/dim]")
        first_chunk = True
        full_response = ""
        try:
            async for chunk in self._app.ai_client.stream(messages):
                if chunk.content:
                    if first_chunk:
                        self.chat_view._current_assistant_message.text = ""
                        self.chat_view._current_assistant_message._refresh()
                        first_chunk = False
                    full_response += chunk.content
                    self.chat_view.stream_chunk(chunk.content)
        except Exception as e:
            if first_chunk:
                self.chat_view._current_assistant_message.text = ""
                first_chunk = False
            error_msg = f"[red]Error: {e}[/red]"
            full_response = error_msg
            self.chat_view.stream_chunk(error_msg)
        self.chat_view.finish_assistant_message()

        self._app.context_builder.history.add(Message(role="user", content=text))
        self._app.context_builder.history.add(Message(role="assistant", content=full_response))
