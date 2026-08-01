"""Tests for multi-provider AI client."""

import pytest

from deepseek_tui.engine.ai_client import (
    AIClient,
    AIProvider,
    Message,
    StreamChunk,
    create_client,
)


class TestMessage:
    def test_user_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self):
        msg = Message(role="system", content="You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."

    def test_to_dict(self):
        msg = Message(role="user", content="Hi")
        assert msg.to_dict() == {"role": "user", "content": "Hi"}


class TestStreamChunk:
    def test_creates_with_content(self):
        chunk = StreamChunk(content="Hello")
        assert chunk.content == "Hello"
        assert chunk.is_done is False

    def test_done_chunk(self):
        chunk = StreamChunk(content="", is_done=True)
        assert chunk.is_done is True


class TestAIProvider:
    def test_all_providers_have_base_url(self):
        for provider in AIProvider:
            assert provider.base_url is not None

    def test_default_model_for_each_provider(self):
        models = {
            AIProvider.DEEPSEEK: "deepseek-reasoner",
            AIProvider.ANTHROPIC: "claude-sonnet-4-6",
            AIProvider.OPENAI: "gpt-4o",
            AIProvider.OLLAMA: "llama3",
        }
        for provider, expected_model in models.items():
            assert provider.default_model == expected_model


class TestCreateClient:
    def test_creates_deepseek_client_with_key(self):
        client = create_client("deepseek", "deepseek-chat", api_key="sk-test")
        assert client.provider == AIProvider.DEEPSEEK

    def test_creates_ollama_client_without_key(self):
        client = create_client("ollama", "llama3")
        assert client.provider == AIProvider.OLLAMA
        assert client.api_key is None

    def test_raises_for_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_client("unknown", "model")


class TestAIClient:
    def test_builds_request_headers(self):
        client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat", api_key="sk-abc")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer sk-abc"
        assert headers["Content-Type"] == "application/json"

    def test_builds_request_body(self):
        client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat")
        messages = [
            Message(role="system", content="You are a note assistant."),
            Message(role="user", content="Summarize my notes."),
        ]
        body = client._build_body(messages)
        assert body["model"] == "deepseek-chat"
        assert body["stream"] is True
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"

    def test_system_prompt_includes_note_context(self, temp_vault):
        from deepseek_tui.engine.vault import VaultReader

        vault = VaultReader(temp_vault)
        note = vault.resolve_wikilink("machine learning basics")

        client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat")
        prompt = client.build_system_prompt(
            context_notes=[note] if note else [],
            permission_level="ask",
        )
        assert "vault" in prompt.content.lower()
        assert "Machine Learning Basics" in prompt.content
