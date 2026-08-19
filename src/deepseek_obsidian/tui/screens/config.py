"""Config screen — interactive settings editor."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from deepseek_obsidian.config.loader import save_config_setting


class ConfigScreen(Screen):
    """Interactive settings editor."""

    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._fields: dict[str, Input] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("[bold]⚙️ Configuration[/bold]", id="config-title")
        with Vertical(id="config-form"):
            yield self._field("provider", "Provider (deepseek/anthropic/openai/ollama)")
            yield self._field("model", "Model name")
            yield self._field("theme", "Theme (dark/light/terminal/dracula/nord...)")
            yield self._field("max_notes", "Max context notes")
            yield self._field("permission_default", "Default permission (ask/review/full)")
        with Horizontal(id="config-actions"):
            yield Button("Save", id="save", variant="primary")
            yield Button("Cancel", id="cancel", variant="error")
        yield Footer()

    def _field(self, key: str, label: str) -> Container:
        c = Container()
        c.mount(Static(f"[dim]{label}[/dim]", classes="field-label"))
        value = str(getattr(self._config, key, ""))
        inp = Input(value=value, id=f"cfg-{key}")
        c.mount(inp)
        self._fields[key] = inp
        return c

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "cancel":
            self.dismiss()

    def action_save(self) -> None:
        # Apply fields back to config object and persist to disk
        provider = self._fields["provider"].value.strip() or self._config.provider
        model = self._fields["model"].value.strip() or self._config.model
        theme = self._fields["theme"].value.strip()
        permission = (
            self._fields["permission_default"].value.strip()
            or self._config.permission_default
        )
        try:
            max_notes = int(self._fields["max_notes"].value)
        except ValueError:
            max_notes = self._config.max_notes

        self._config.provider = provider
        self._config.model = model
        self._config.theme = theme
        self._config.permission_default = permission
        self._config.max_notes = max_notes

        # Persist to config.toml
        save_config_setting("model", "provider", provider)
        save_config_setting("model", "model", model)
        save_config_setting("tui", "theme", theme)
        save_config_setting("tui", "permission_default", permission)
        save_config_setting("context", "max_notes", str(max_notes))
        self.dismiss()
