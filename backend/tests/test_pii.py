"""Tests for PII masking helpers."""
import pytest

from ai.pii import mask_candidate_row, mask_email


class TestMaskEmail:
    def test_basic_mask(self):
        assert mask_email("alice@example.com") == "a***@example.com"

    def test_single_letter_local(self):
        assert mask_email("a@example.com") == "a***@example.com"

    def test_preserves_domain(self):
        assert mask_email("david.bala@university.ro") == "d***@university.ro"

    @pytest.mark.parametrize("bad", ["", None, "notanemail", "@nodomain", "no-at-sign"])
    def test_invalid_returns_empty(self, bad):
        assert mask_email(bad) == ""


class TestMaskCandidateRow:
    def test_email_masked(self):
        row = {"name": "Alice", "email": "alice@example.com", "linkedin_url": "x"}
        out = mask_candidate_row(row)
        assert out["email"] == "a***@example.com"
        assert out["email_masked"] is True
        assert out["name"] == "Alice"

    def test_no_email_marks_unmasked(self):
        row = {"name": "Alice", "email": ""}
        out = mask_candidate_row(row)
        assert out["email"] == ""
        assert out["email_masked"] is False

    def test_does_not_mutate_original(self):
        row = {"name": "Alice", "email": "alice@example.com"}
        mask_candidate_row(row)
        assert row["email"] == "alice@example.com"
