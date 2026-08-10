"""Context builder — searches vault and assembles prompts with note context."""

from __future__ import annotations

import re
from pathlib import Path

from deepseek_obsidian.engine.ai_client import AIClient, AIProvider, Message
from deepseek_obsidian.engine.vault import Note, VaultReader

WIKILINK_IN_QUERY = re.compile(r"\[\[([^\]]+)\]\]")


class ChatHistory:
    """Ring-buffer for chat messages with session persistence."""

    def __init__(self, max_messages: int = 50, session_path: Path | None = None):
        self.max_messages = max_messages
        self._messages: list[Message] = []
        self._session_path = session_path

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    def add(self, message: Message) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]
        self._save()

    def clear(self) -> None:
        self._messages.clear()
        self._save()

    def _save(self) -> None:
        if not self._session_path:
            return
        try:
            import json
            self._session_path.parent.mkdir(parents=True, exist_ok=True)
            data = [m.to_dict() for m in self._messages]
            self._session_path.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def load(self) -> int:
        """Load messages from session file. Returns count of restored messages."""
        if not self._session_path or not self._session_path.exists():
            return 0
        try:
            import json
            data = json.loads(self._session_path.read_text())
            self._messages = [Message(**m) for m in data]
            return len(self._messages)
        except Exception:
            return 0


class ContextBuilder:
    """Builds AI prompts by searching the vault and assembling context."""

    def __init__(
        self, vault: VaultReader, max_notes: int = 10,
        session_path: Path | None = None,
    ):
        self.vault = vault
        self.max_notes = max_notes
        self.history = ChatHistory(session_path=session_path)
        if session_path:
            restored = self.history.load()
            if restored:
                self._restored_count = restored
            else:
                self._restored_count = 0
        else:
            self._restored_count = 0

    @property
    def restored_count(self) -> int:
        return self._restored_count

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
        model: str = "",
    ) -> tuple[list[Message], list[Note]]:
        """Build the full message list for an AI request.

        Args:
            query: The user's message.
            permission_level: Current permission posture.
            model: Model name (used in system prompt context).

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

        # Fallback: always include a note index so the AI can navigate
        if not context_notes:
            context_notes = self.vault.notes[:self.max_notes]

        # Build system prompt (model-agnostic, just builds text)
        client = AIClient(AIProvider.DEEPSEEK, model or "deepseek-v4-flash")
        system_msg = client.build_system_prompt(context_notes, permission_level)

        # Assemble full message list
        messages: list[Message] = [system_msg]
        messages.extend(self.history.messages)
        messages.append(Message(role="user", content=query))

        return messages, context_notes
