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
            "deepseek": [
                "deepseek-chat", "deepseek-reasoner",
                "deepseek-v4-flash", "deepseek-v4-pro",
            ],
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
    reasoning: str = ""  # Chain-of-thought from reasoning models
    is_done: bool = False


class AIClient:
    """Handles communication with AI providers using OpenAI-compatible API."""

    def __init__(self, provider: AIProvider, model: str, api_key: str | None = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.last_actual_model: str = ""  # What the API actually ran

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
            "You are an AI agent with full vault access. "
            "The notes BELOW are already loaded. Read them — don't ask to.",
            f"Write permission: {permission_level}.",
            "",
            "RULES:",
            "1. The notes below ARE visible to you. Never say you can't access them.",
            "2. If information isn't in the notes, say so briefly and suggest what to search for.",
            "3. Reference notes as [[exact title]].",
            "4. Be concise — this is a terminal.",
            "",
        ]

        if permission_level == "ask":
            lines.append(
                "You can READ and ANALYZE notes. "
                "Suggest edits (cannot apply them)."
            )
        elif permission_level in ("review", "full"):
            lines.append(
                "You can EDIT notes. To apply an edit that the user can accept:"
            )
            lines.append("")
            lines.append(
                "---PROPOSE title=\"Note Title\"\n"
                "exact text to replace (copy from the note above)\n"
                "+++\n"
                "replacement text\n"
                "---ENDPROPOSE"
            )
        if permission_level == "full":
            lines.append(
                "FULL ACCESS: propose edits freely — "
                "accepted with one click."
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
                            if not self.last_actual_model:
                                self.last_actual_model = chunk.get("model", "")
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            reasoning = delta.get("reasoning_content", "")
                            if content or reasoning:
                                yield StreamChunk(
                                    content=content,
                                    reasoning=reasoning,
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        yield StreamChunk(content="", is_done=True)


def create_client(provider: str, model: str, api_key: str | None = None) -> AIClient:
    """Factory function to create an AI client for a given provider."""
    prov = AIProvider.from_string(provider)
    return AIClient(prov, model, api_key)
