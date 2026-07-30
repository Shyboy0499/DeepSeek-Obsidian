"""Multi-provider AI client with streaming support."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum

import httpx

from deepseek_tui.engine.vault import Note


class AIProvider(Enum):
    base_url: str
    default_model: str

    DEEPSEEK = ("deepseek", "https://api.deepseek.com/v1", "deepseek-chat")
    ANTHROPIC = ("anthropic", "https://api.anthropic.com/v1", "claude-sonnet-4-6")
    OPENAI = ("openai", "https://api.openai.com/v1", "gpt-4o")
    OLLAMA = ("ollama", "http://localhost:11434/v1", "llama3")

    def __new__(cls, value: str, base_url: str, default_model: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.base_url = base_url
        obj.default_model = default_model
        return obj

    @classmethod
    def from_string(cls, s: str) -> AIProvider:
        for provider in cls:
            if provider.value == s.lower():
                return provider
        raise ValueError(f"Unknown provider: {s}")

    @classmethod
    def known_models(cls) -> dict[str, list[str]]:
        return {
            "deepseek": ["deepseek-chat", "deepseek-reasoner"],
            "anthropic": ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5"],
            "openai": ["gpt-4o", "gpt-4o-mini"],
            "ollama": ["llama3", "mistral", "codellama", "phi3"],
        }


@dataclass
class Message:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class StreamChunk:
    content: str
    is_done: bool = False


class AIClient:
    """Handles communication with AI providers using OpenAI-compatible API."""

    def __init__(self, provider: AIProvider, model: str, api_key: str | None = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_body(self, messages: list[Message]) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }

    def build_system_prompt(
        self,
        context_notes: list[Note],
        permission_level: str = "ask",
    ) -> Message:
        lines = [
            "You are an AI note-taking and research assistant.",
            "You have access to the user's Obsidian vault.",
            f"Current permission level: {permission_level}.",
            "",
        ]

        if permission_level == "ask":
            lines.append(
                "You may READ notes, SEARCH the vault, and SUGGEST links or edits. "
                "You may NOT write to the vault."
            )
        elif permission_level in ("review", "full"):
            lines.append(
                "You may READ notes, SEARCH the vault, PROPOSE edits, and DRAFT notes. "
                "Proposed changes will be reviewed by the user before being written."
            )
            lines.append("")
            lines.append(
                "To propose an edit to an existing note, use this format:\n"
                "```\n"
                "---PROPOSE title=\"Note Title\"\n"
                "the exact text to find and replace\n"
                "+++\n"
                "the new replacement text\n"
                "---ENDPROPOSE\n"
                "```\n"
                "The old text must match exactly (including whitespace) "
                "for the edit to be applied."
            )
        if permission_level == "full":
            lines.append(
                "You have FULL ACCESS. You may read, edit, and create notes. "
                "All writes are logged to an audit trail."
            )

        if context_notes:
            lines.append("")
            lines.append("## Relevant Notes from Vault")
            for note in context_notes:
                rel_path = note.path.name
                lines.append(f"### {note.title} (`{rel_path}`)")
                if note.tags:
                    lines.append(f"Tags: {', '.join(note.tags)}")
                lines.append(note.preview(max_chars=500))
                lines.append("")

        return Message(role="system", content="\n".join(lines))

    async def stream(
        self,
        messages: list[Message],
    ) -> AsyncIterator[StreamChunk]:
        body = self._build_body(messages)

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.provider.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            yield StreamChunk(content="", is_done=True)
                            return
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        yield StreamChunk(content="", is_done=True)


def create_client(provider: str, model: str, api_key: str | None = None) -> AIClient:
    """Factory function to create an AI client for a given provider."""
    prov = AIProvider.from_string(provider)
    return AIClient(prov, model, api_key)
