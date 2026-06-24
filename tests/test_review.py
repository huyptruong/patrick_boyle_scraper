"""Tests for local summary reviewer."""

from __future__ import annotations

from pathlib import Path

import pytest

from dashboard.review import (
    pending_queue,
    prepare_video_rows,
    queue_counts,
    save_replacement_summary,
    validate_replacement_summary,
)
from scraper.csv_io import read_failed_ids, read_summaries, record_failed_id, write_summaries
from tests.test_csv_io import _video_row
from scraper.csv_io import write_metadata


def _row(
    video_id: str,
    *,
    summary: str = "",
    upload_date: str = "20260615",
    title: str = "",
) -> dict[str, str]:
    return {
        **_video_row(video_id, title or video_id),
        "summary": summary,
        "upload_date": upload_date,
    }


def test_prepare_video_rows_adds_status_and_month() -> None:
    rows = prepare_video_rows(
        [
            _row("a", summary="Real summary."),
            _row("b", summary="https://www.youtube.com/watch?v=b", upload_date="20260101"),
        ]
    )
    assert rows[0]["status"] == "complete"
    assert rows[0]["upload_month"] == "2026-06"
    assert rows[1]["status"] == "pending"
    assert rows[1]["upload_month"] == "2026-01"


def test_pending_queue_returns_only_pending_rows() -> None:
    rows = prepare_video_rows(
        [
            _row("a", summary="Done."),
            _row("b", summary="https://www.youtube.com/watch?v=b"),
            _row("c", summary=""),
        ]
    )
    queue = pending_queue(rows)
    assert [row["id"] for row in queue] == ["b"]


def test_pending_queue_empty_when_no_url_placeholders() -> None:
    rows = prepare_video_rows([_row("a", summary="Done.")])
    assert pending_queue(rows) == []


def test_pending_queue_slice_filter() -> None:
    rows = prepare_video_rows(
        [
            _row(
                "a",
                summary="https://www.youtube.com/watch?v=a",
                upload_date="20260115",
            ),
            _row(
                "b",
                summary="https://www.youtube.com/watch?v=b",
                upload_date="20260215",
            ),
        ]
    )
    queue = pending_queue(rows, slice_month="2026-01")
    assert [row["id"] for row in queue] == ["a"]


def test_queue_counts() -> None:
    rows = prepare_video_rows(
        [
            _row("a", summary="Done."),
            _row("b", summary="https://www.youtube.com/watch?v=b"),
            _row("c", summary=""),
        ]
    )
    assert queue_counts(rows) == {"complete": 1, "pending": 1, "missing": 1}


def test_validate_replacement_summary_rejects_empty() -> None:
    assert validate_replacement_summary("") == "Summary cannot be empty."
    assert validate_replacement_summary("   ") == "Summary cannot be empty."


def test_validate_replacement_summary_rejects_url() -> None:
    assert (
        validate_replacement_summary("https://www.youtube.com/watch?v=x")
        == "Summary still looks like a URL. Paste the full summary text."
    )


def test_validate_replacement_summary_accepts_real_text() -> None:
    assert validate_replacement_summary("Patrick Boyle discusses markets.") is None


def test_save_replacement_summary_writes_csv_and_clears_failed_id(tmp_path: Path) -> None:
    videos_path = tmp_path / "videos.csv"
    summaries_path = tmp_path / "summaries.csv"
    failed_path = tmp_path / "failed_ids.txt"

    write_metadata([_video_row("a", "Video A")], videos_path)
    write_summaries(
        {"a": "https://www.youtube.com/watch?v=a"},
        summaries_path,
    )
    record_failed_id("a", failed_path)

    save_replacement_summary(
        "a",
        "Replacement summary text.",
        summaries_path=summaries_path,
        failed_ids_path=failed_path,
    )

    assert read_summaries(summaries_path)["a"] == "Replacement summary text."
    assert read_failed_ids(failed_path) == []


def test_review_app_imports_like_streamlit() -> None:
    """Streamlit puts dashboard/ on sys.path; review_app must still import."""
    import importlib.util
    import sys

    root = Path(__file__).resolve().parent.parent
    dashboard_dir = str(root / "dashboard")
    saved_path = sys.path.copy()
    try:
        sys.path = [dashboard_dir, *[p for p in sys.path if p not in {dashboard_dir, str(root)}]]
        spec = importlib.util.spec_from_file_location(
            "review_entry",
            root / "dashboard" / "review.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert callable(module.main)
    finally:
        sys.path[:] = saved_path
