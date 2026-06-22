"""Tests for extract_summaries video selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from extract_summaries import _select_metadata_rows


def _metadata() -> list[dict[str, str]]:
    return [
        {"id": "first", "title": "First"},
        {"id": "second", "title": "Second"},
        {"id": "third", "title": "Third"},
    ]


def test_select_metadata_rows_by_video_ids() -> None:
    rows = _select_metadata_rows(
        _metadata(),
        video_ids=["third", "first"],
        max_videos=None,
        input_path=Path("videos.csv"),
    )

    assert [row["id"] for row in rows] == ["third", "first"]


def test_select_metadata_rows_by_max_videos() -> None:
    rows = _select_metadata_rows(
        _metadata(),
        video_ids=[],
        max_videos=2,
        input_path=Path("videos.csv"),
    )

    assert [row["id"] for row in rows] == ["first", "second"]


def test_select_metadata_rows_returns_all_when_no_filters() -> None:
    rows = _select_metadata_rows(
        _metadata(),
        video_ids=[],
        max_videos=None,
        input_path=Path("videos.csv"),
    )

    assert len(rows) == 3


def test_select_metadata_rows_missing_id_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        _select_metadata_rows(
            _metadata(),
            video_ids=["missing"],
            max_videos=None,
            input_path=Path("videos.csv"),
        )


def test_count_videos_to_extract_respects_skip_existing() -> None:
    from extract_summaries import _count_videos_to_extract

    metadata = _metadata()
    summaries = {"first": "already done"}
    assert _count_videos_to_extract(
        metadata,
        summaries,
        skip_existing=True,
        explicit_video_ids=False,
    ) == 2
    assert _count_videos_to_extract(
        metadata,
        summaries,
        skip_existing=False,
        explicit_video_ids=False,
    ) == 3
