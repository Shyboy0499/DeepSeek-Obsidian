"""Chat view widget — displays streaming AI responses with markdown rendering."""

from textual.containers import VerticalScroll
from textual.widgets import Static


class ChatMessage(Static):
    """A single message bubble in the chat."""

    def __init__(self, role: str, content: str = ""):
        super().__init__("")
        self.role = role
        self.content = content

    def on_mount(self) -> None:
        self._render()

    def _render(self) -> None:
        if self.role == "user":
            prefix = "🧑 You"
        elif self.role == "assistant":
            prefix = "🤖 Assistant"
        else:
            prefix = "⚙️ System"

        self.update(f"[bold]{prefix}[/bold]\n\n{self.content}")

    def append_chunk(self, chunk: str) -> None:
        """Stream a chunk of content to this message."""
        self.content += chunk
        self._render()


class ChatView(VerticalScroll):
    """Scrollable chat view that holds ChatMessage widgets."""

    def __init__(self):
        super().__init__()
        self._current_assistant_message: ChatMessage | None = None

    def add_user_message(self, content: str) -> None:
        msg = ChatMessage(role="user", content=content)
        self.mount(msg)
        self.scroll_end()

    def start_assistant_message(self) -> None:
        msg = ChatMessage(role="assistant", content="")
        self._current_assistant_message = msg
        self.mount(msg)

    def stream_chunk(self, chunk: str) -> None:
        if self._current_assistant_message:
            self._current_assistant_message.append_chunk(chunk)
            self.scroll_end()

    def finish_assistant_message(self) -> None:
        self._current_assistant_message = None

    def clear_chat(self) -> None:
        self.remove_children()
        self._current_assistant_message = None
