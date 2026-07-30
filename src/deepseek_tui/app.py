"""Application entry point."""

from __future__ import annotations

from textual.app import App


def main() -> None:
    """Launch the DeepSeek-Tui application."""
    from deepseek_tui.tui.screen import MainScreen

    class DeepSeekTuiApp(App):
        def on_mount(self) -> None:
            self.push_screen(MainScreen())

    app = DeepSeekTuiApp()
    app.run()


if __name__ == "__main__":
    main()
