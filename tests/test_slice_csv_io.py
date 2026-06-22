"""Tests for slice-aware metadata CSV writes."""

from __future__ import annotations

from pathlib import Path

from scraper.config import VIDEO_FIELDS
from scraper.csv_io import read_metadata_if_exists, remove_summaries_for_video_ids, write_metadata_for_slice


def _row(video_id: str, upload_date: str) -> dict[str, str]:
    return {field: "" for field in VIDEO_FIELDS} | {
        "id": video_id,
        "upload_date": upload_date,
        "title": video_id,
    }


def test_write_metadata_for_slice_appends_month(tmp_path: Path) -> None:
    path = tmp_path / "videos.csv"
    write_metadata_for_slice([_row("june", "20260601")], "202606", path)

    write_metadata_for_slice([_row("may", "20260515")], "202605", path)

    rows = read_metadata_if_exists(path)
    assert [row["id"] for row in rows] == ["june", "may"]


def test_write_metadata_for_slice_refresh_replaces_month(tmp_path: Path) -> None:
    path = tmp_path / "videos.csv"
    write_metadata_for_slice([_row("old", "20260601")], "202606", path)
    write_metadata_for_slice(
        [_row("new", "20260620")],
        "202606",
        path,
        refresh=True,
    )

    rows = read_metadata_if_exists(path)
    assert [row["id"] for row in rows] == ["new"]


def test_remove_summaries_for_video_ids(tmp_path: Path) -> None:
    from scraper.csv_io import read_summaries, write_summaries

    path = tmp_path / "summaries.csv"
    write_summaries(
        {"june": "June text", "may": "May text"},
        path,
        replace_all=True,
    )

    remove_summaries_for_video_ids({"june"}, path)

    assert read_summaries(path) == {"may": "May text"}
