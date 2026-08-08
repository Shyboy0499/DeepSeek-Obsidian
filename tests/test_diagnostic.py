"""Diagnostic tests — designed to pinpoint WHY something failed.

These are the tests you run when a bug report comes in. Each test
isolates one component and validates edge cases that commonly break.
"""

import pytest
from deepseek_obsidian.tui.screen import _parse_proposals, _clean_response


class TestProposalParserDiagnostics:
    """Diagnose why an edit proposal wasn't applied."""

    def test_empty_title_fails_gracefully(self):
        """Bug: empty title in proposal crashes the parser."""
        text = '---PROPOSE title=""\nold\n+++\nnew\n---ENDPROPOSE'
        proposals = _parse_proposals(text)
        assert len(proposals) == 0  # Should not crash

    def test_malformed_no_end_marker(self):
        """Bug: missing ENDPROPOSE means proposal is ignored."""
        text = '---PROPOSE title="Note"\nold\n+++\nnew'
        proposals = _parse_proposals(text)
        assert len(proposals) == 0  # Won't match without ENDPROPOSE

    def test_proposal_with_leading_trailing_whitespace_in_title(self):
        """Bug: whitespace in title causes resolve_wikilink to miss."""
        text = '---PROPOSE title="  My Note  "\nold\n+++\nnew\n---ENDPROPOSE'
        proposals = _parse_proposals(text)
        assert len(proposals) == 1
        assert proposals[0]["title"] == "  My Note  "

    def test_multiline_old_text(self):
        """Bug: single-line old text fails for multi-line replacements."""
        text = (
            '---PROPOSE title="Note"\n'
            'line one\nline two\nline three\n'
            '+++\n'
            'replacement\n'
            '---ENDPROPOSE'
        )
        proposals = _parse_proposals(text)
        assert len(proposals) == 1
        assert "line one" in proposals[0]["old"]

    def test_special_characters_in_proposal(self):
        """Bug: regex chars in note content break the parser."""
        text = (
            '---PROPOSE title="Note"\n'
            'price: $50 (50% off) *special*\n'
            '+++\n'
            'price: $60\n'
            '---ENDPROPOSE'
        )
        proposals = _parse_proposals(text)
        assert len(proposals) == 1
        assert "$50" in proposals[0]["old"]

    def test_multiple_proposals_same_note(self):
        """Multiple proposals for the same note should all parse."""
        text = (
            '---PROPOSE title="Note A"\nold1\n+++\nnew1\n---ENDPROPOSE\n\n'
            '---PROPOSE title="Note A"\nold2\n+++\nnew2\n---ENDPROPOSE'
        )
        proposals = _parse_proposals(text)
        assert len(proposals) == 2
        assert proposals[0]["title"] == "Note A"
        assert proposals[1]["title"] == "Note A"


class TestCleanResponseDiagnostics:
    """Diagnose why cleanup left markup in the displayed response."""

    def test_cleaned_response_has_no_markup(self):
        text = (
            'Before text\n'
            '---PROPOSE title="X"\nold\n+++\nnew\n---ENDPROPOSE\n'
            'After text'
        )
        cleaned = _clean_response(text)
        assert "---PROPOSE" not in cleaned
        assert "---ENDPROPOSE" not in cleaned
        assert "Before text" in cleaned
        assert "After text" in cleaned

    def test_no_proposals_returns_unchanged(self):
        text = "Just a normal response with nothing special."
        assert _clean_response(text) == text

    def test_only_proposals_returns_empty(self):
        text = '---PROPOSE title="X"\nold\n+++\nnew\n---ENDPROPOSE'
        cleaned = _clean_response(text)
        assert len(cleaned) == 0
