"""Context builder — searches vault and assembles prompts with note context."""

from __future__ import annotations

import re

from deepseek_tui.engine.ai_client import AIClient, AIProvider, Message
from deepseek_tui.engine.vault import Note, VaultReader

WIKILINK_IN_QUERY = re.compile(r"\[\[([^\]]+)\]\]")


class ChatHistory:
    """Ring-buffer for chat messages."""

    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._messages: list[Message] = []

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    def add(self, message: Message) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def clear(self) -> None:
        self._messages.clear()


class ContextBuilder:
    """Builds AI prompts by searching the vault and assembling context."""

    def __init__(self, vault: VaultReader, max_notes: int = 10):
        self.vault = vault
        self.max_notes = max_notes
        self.history = ChatHistory()

    def _extract_wikilinks(self, query: str) -> list[Note]:
        """Find notes explicitly referenced via [[wikilinks]] in the query."""
        links = WIKILINK_IN_QUERY.findall(query)
        notes: list[Note] = []
        for link in links:
            note = self.vault.resolve_wikilink(link)
            if note:
                notes.append(note)
        return notes

    def _search_vault(self, query: str) -> list[Note]:
        """Quick pass: title search. Falls back to full-text."""
        results = self.vault.search_by_title(query)
        if not results:
            results = self.vault.search_full_text(query)
        return results[:self.max_notes]

    def build(
        self,
        query: str,
        permission_level: str = "ask",
    ) -> tuple[list[Message], list[Note]]:
        """Build the full message list for an AI request.

        Returns:
            Tuple of (messages, context_notes).
        """
        # Gather context notes
        linked_notes = self._extract_wikilinks(query)
        searched_notes = self._search_vault(query)

        # Merge: linked notes first, then searched, deduplicate by path
        seen = {n.path for n in linked_notes}
        context_notes = list(linked_notes)
        for note in searched_notes:
            if note.path not in seen:
                context_notes.append(note)
                seen.add(note.path)
        context_notes = context_notes[:self.max_notes]

        # Build system prompt
        client = AIClient(AIProvider.DEEPSEEK, "deepseek-chat")
        system_msg = client.build_system_prompt(context_notes, permission_level)

        # Assemble full message list
        messages: list[Message] = [system_msg]
        messages.extend(self.history.messages)
        messages.append(Message(role="user", content=query))

        return messages, context_notes
