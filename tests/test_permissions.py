"""Tests for permission model and audit trail."""

import json
import tempfile
from pathlib import Path

import pytest
from deepseek_tui.engine.permissions import (
    AuditEntry,
    AuditTrail,
    PermissionLevel,
    Permissions,
)


class TestPermissionLevel:
    def test_ask_allows_read_only(self):
        perm = PermissionLevel.ASK
        assert perm.allows_read() is True
        assert perm.allows_propose() is False
        assert perm.allows_write() is False

    def test_auto_review_allows_read_and_propose(self):
        perm = PermissionLevel.AUTO_REVIEW
        assert perm.allows_read() is True
        assert perm.allows_propose() is True
        assert perm.allows_write() is False

    def test_full_access_allows_everything(self):
        perm = PermissionLevel.FULL_ACCESS
        assert perm.allows_read() is True
        assert perm.allows_propose() is True
        assert perm.allows_write() is True

    def test_cycle_next_rotates(self):
        assert PermissionLevel.ASK.next() == PermissionLevel.AUTO_REVIEW
        assert PermissionLevel.AUTO_REVIEW.next() == PermissionLevel.FULL_ACCESS
        assert PermissionLevel.FULL_ACCESS.next() == PermissionLevel.ASK

    def test_from_string(self):
        assert PermissionLevel.from_string("ask") == PermissionLevel.ASK
        assert PermissionLevel.from_string("review") == PermissionLevel.AUTO_REVIEW
        assert PermissionLevel.from_string("full") == PermissionLevel.FULL_ACCESS
        with pytest.raises(ValueError):
            PermissionLevel.from_string("invalid")


class TestPermissions:
    def test_default_is_ask(self):
        p = Permissions()
        assert p.level == PermissionLevel.ASK

    def test_cycle_changes_level(self):
        p = Permissions()
        p.cycle()
        assert p.level == PermissionLevel.AUTO_REVIEW
        p.cycle()
        assert p.level == PermissionLevel.FULL_ACCESS
        p.cycle()
        assert p.level == PermissionLevel.ASK

    def test_set_level(self):
        p = Permissions()
        p.set_level(PermissionLevel.FULL_ACCESS)
        assert p.level == PermissionLevel.FULL_ACCESS

    def test_ask_rejects_writes(self):
        p = Permissions()
        assert p.can_write() is False

    def test_full_access_allows_write(self):
        p = Permissions()
        p.set_level(PermissionLevel.FULL_ACCESS)
        assert p.can_write() is True


class TestAuditTrail:
    def test_records_entries(self):
        trail = AuditTrail()
        trail.record("write", "note1.md", "added [[link]] to content")
        assert len(trail.entries) == 1
        assert trail.entries[0].action == "write"
        assert trail.entries[0].target == "note1.md"

    def test_last_entry_returns_most_recent(self):
        trail = AuditTrail()
        trail.record("read", "note1.md", "")
        trail.record("write", "note2.md", "created note")
        assert trail.last_entry is not None
        assert trail.last_entry.action == "write"

    def test_save_and_load(self):
        trail = AuditTrail()
        trail.record("write", "note1.md", "edit")
        trail.record("write", "note2.md", "create")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            trail.save(Path(f.name))
            path = f.name

        loaded = AuditTrail.load(Path(path))
        Path(path).unlink()

        assert len(loaded.entries) == 2
        assert loaded.entries[0].target == "note1.md"
        assert loaded.entries[1].target == "note2.md"

    def test_can_undo_last_write(self):
        trail = AuditTrail()
        trail.record("write", "note1.md", "edit", previous_content="old content")
        entry = trail.pop_last_write()
        assert entry is not None
        assert entry.target == "note1.md"
        assert entry.previous_content == "old content"
        assert len(trail.entries) == 0
