"""Main TUI screen with chat-primary layout, sidebar, header, and input bar."""

from textual.screen import Screen
from textual.containers import Container

from deepseek_tui.tui.widgets.header import Header
from deepseek_tui.tui.widgets.chat import ChatView
from deepseek_tui.tui.widgets.sidebar import Sidebar
from deepseek_tui.tui.widgets.input_bar import InputBar


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
