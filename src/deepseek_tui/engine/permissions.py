"""Progressive permission model for note operations and audit trail."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PermissionLevel(Enum):
    ASK = "ask"
    AUTO_REVIEW = "review"
    FULL_ACCESS = "full"

    def allows_read(self) -> bool:
        return True

    def allows_propose(self) -> bool:
        return self in (PermissionLevel.AUTO_REVIEW, PermissionLevel.FULL_ACCESS)

    def allows_write(self) -> bool:
        return self == PermissionLevel.FULL_ACCESS

    def next(self) -> PermissionLevel:
        levels = list(PermissionLevel)
        idx = levels.index(self)
        return levels[(idx + 1) % len(levels)]

    @classmethod
    def from_string(cls, s: str) -> PermissionLevel:
        mapping = {
            "ask": cls.ASK,
            "review": cls.AUTO_REVIEW,
            "full": cls.FULL_ACCESS,
        }
        if s.lower() not in mapping:
            raise ValueError(f"Unknown permission level: {s}")
        return mapping[s.lower()]


@dataclass
class AuditEntry:
    timestamp: float = field(default_factory=time.time)
    action: str = ""
    target: str = ""
    detail: str = ""
    previous_content: str = ""


class AuditTrail:
    """Append-only log of all write operations for review and undo."""

    def __init__(self):
        self._entries: list[AuditEntry] = []

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    @property
    def last_entry(self) -> AuditEntry | None:
        return self._entries[-1] if self._entries else None

    def record(self, action: str, target: str, detail: str, previous_content: str = "") -> None:
        self._entries.append(AuditEntry(
            action=action,
            target=target,
            detail=detail,
            previous_content=previous_content,
        ))

    def pop_last_write(self) -> AuditEntry | None:
        for i in range(len(self._entries) - 1, -1, -1):
            if self._entries[i].action == "write":
                return self._entries.pop(i)
        return None

    def save(self, path: Path) -> None:
        data = [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "target": e.target,
                "detail": e.detail,
                "previous_content": e.previous_content,
            }
            for e in self._entries
        ]
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> AuditTrail:
        trail = cls()
        if path.exists():
            data = json.loads(path.read_text())
            for entry in data:
                trail._entries.append(AuditEntry(
                    timestamp=entry["timestamp"],
                    action=entry["action"],
                    target=entry["target"],
                    detail=entry["detail"],
                    previous_content=entry.get("previous_content", ""),
                ))
        return trail


class Permissions:
    """Manages current permission level for the session."""

    def __init__(self, level: PermissionLevel = PermissionLevel.ASK):
        self.level = level
        self._audit_trail = AuditTrail()

    @property
    def audit_trail(self) -> AuditTrail:
        return self._audit_trail

    def cycle(self) -> PermissionLevel:
        self.level = self.level.next()
        return self.level

    def set_level(self, level: PermissionLevel) -> None:
        self.level = level

    def can_propose(self) -> bool:
        return self.level.allows_propose()

    def can_write(self) -> bool:
        return self.level.allows_write()
