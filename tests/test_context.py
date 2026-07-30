"""Tests for context builder."""

from deepseek_tui.engine.context import ContextBuilder, ChatHistory
from deepseek_tui.engine.ai_client import Message
from deepseek_tui.engine.vault import VaultReader


class TestChatHistory:
    def test_adds_messages(self):
        history = ChatHistory(max_messages=10)
        history.add(Message(role="user", content="Hello"))
        history.add(Message(role="assistant", content="Hi there"))
        assert len(history.messages) == 2

    def test_trims_oldest_when_over_limit(self):
        history = ChatHistory(max_messages=3)
        for i in range(5):
            history.add(Message(role="user", content=str(i)))
        assert len(history.messages) == 3
        assert history.messages[0].content == "2"
        assert history.messages[-1].content == "4"

    def test_clear_removes_all(self):
        history = ChatHistory()
        history.add(Message(role="user", content="Hi"))
        history.clear()
        assert len(history.messages) == 0


class TestContextBuilder:
    def test_builds_context_from_query(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=5)

        messages, context_notes = builder.build("machine learning")
        assert len(messages) >= 2
        assert messages[0].role == "system"
        assert messages[-1].role == "user"
        assert messages[-1].content == "machine learning"

    def test_includes_wikilinked_note_when_mentioned(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=5)

        messages, context_notes = builder.build("tell me about [[Neural Networks]]")
        system = messages[0].content
        assert "Neural Networks" in system

    def test_limits_context_notes_to_max(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=1)

        messages, context_notes = builder.build("notes")
        assert len(context_notes) <= 1

    def test_includes_chat_history(self, temp_vault):
        vault = VaultReader(temp_vault)
        builder = ContextBuilder(vault, max_notes=5)
        builder.history.add(Message(role="user", content="What is ML?"))
        builder.history.add(Message(role="assistant", content="ML is..."))

        messages, context_notes = builder.build("tell me more")
        # Should have: system + user (history) + assistant (history) + user (new) = 4
        assert len(messages) >= 3
