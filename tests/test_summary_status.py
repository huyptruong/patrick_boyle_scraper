"""Tests for summary status classification."""

from __future__ import annotations

from scraper.summary_status import parse_upload_month, summary_status


def test_summary_status_missing_for_empty() -> None:
    assert summary_status("") == "missing"
    assert summary_status("   ") == "missing"


def test_summary_status_pending_for_url_placeholder() -> None:
    assert (
        summary_status("https://www.youtube.com/watch?v=iBlu45HFruk")
        == "pending"
    )
    assert summary_status("  HTTP://example.com") == "pending"


def test_summary_status_complete_for_real_text() -> None:
    assert summary_status("This video explores markets.") == "complete"


def test_parse_upload_month() -> None:
    assert parse_upload_month("20260620") == "2026-06"
    assert parse_upload_month("20260101") == "2026-01"
    assert parse_upload_month("") == ""
    assert parse_upload_month("bad") == ""
