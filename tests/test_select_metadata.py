"""Tests for extract_plan video selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from scraper.extract_plan import count_videos_to_extract, select_metadata_rows


def _metadata() -> list[dict[str, str]]:
    return [
        {"id": "first", "title": "First", "upload_date": "20260601"},
        {"id": "second", "title": "Second", "upload_date": "20260615"},
        {"id": "third", "title": "Third", "upload_date": "20260501"},
    ]


def test_select_metadata_rows_by_video_ids() -> None:
    rows = select_metadata_rows(
        _metadata(),
        video_ids=["third", "first"],
        max_videos=None,
        input_path=Path("videos.csv"),
        slice_yyyymm=None,
    )

    assert [row["id"] for row in rows] == ["third", "first"]


def test_select_metadata_rows_by_max_videos() -> None:
    rows = select_metadata_rows(
        _metadata(),
        video_ids=[],
        max_videos=2,
        input_path=Path("videos.csv"),
    )

    assert [row["id"] for row in rows] == ["first", "second"]


def test_select_metadata_rows_returns_all_when_no_filters() -> None:
    rows = select_metadata_rows(
        _metadata(),
        video_ids=[],
        max_videos=None,
        input_path=Path("videos.csv"),
    )

    assert len(rows) == 3


def test_select_metadata_rows_missing_id_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        select_metadata_rows(
            _metadata(),
            video_ids=["missing"],
            max_videos=None,
            input_path=Path("videos.csv"),
        )


def test_count_videos_to_extract_respects_skip_existing() -> None:
    metadata = _metadata()
    summaries = {"first": "already done"}
    assert count_videos_to_extract(
        metadata,
        summaries,
        skip_existing=True,
        explicit_video_ids=False,
    ) == 2
    assert count_videos_to_extract(
        metadata,
        summaries,
        skip_existing=False,
        explicit_video_ids=False,
    ) == 3


def test_select_metadata_rows_filters_by_slice() -> None:
    rows = select_metadata_rows(
        _metadata(),
        video_ids=[],
        max_videos=None,
        input_path=Path("videos.csv"),
        slice_yyyymm="202606",
    )

    assert [row["id"] for row in rows] == ["first", "second"]
