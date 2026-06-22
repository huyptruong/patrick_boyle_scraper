"""Tests for csv_io read/write helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from csv_io import (
    _atomic_write_csv,
    clear_failed_id,
    merge_videos_and_summaries,
    read_failed_ids,
    read_metadata,
    read_summaries,
    record_failed_id,
    write_combined_csv,
    write_metadata,
    write_summaries,
)
from config import SUMMARY_FIELDS, VIDEO_FIELDS


def _video_row(video_id: str, title: str = "") -> dict[str, str]:
    return {
        "id": video_id,
        "title": title or video_id,
        "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
        "view_count": "",
        "like_count": "",
        "upload_date": "",
        "duration": "",
        "description": "",
        "channel": "",
        "thumbnail": "",
    }


def test_read_metadata_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "videos.csv"
    with pytest.raises(FileNotFoundError, match="not found"):
        read_metadata(missing)


def test_write_summaries_merges_without_losing_rows(tmp_path: Path) -> None:
    path = tmp_path / "summaries.csv"
    write_summaries({"a": "summary a"}, path)
    write_summaries({"b": "summary b"}, path)

    summaries = read_summaries(path)
    assert summaries == {"a": "summary a", "b": "summary b"}


def test_write_summaries_respects_video_order(tmp_path: Path) -> None:
    path = tmp_path / "summaries.csv"
    write_summaries(
        {"c": "third", "a": "first", "b": "second"},
        path,
        video_order=["a", "b", "c", "d"],
    )

    with path.open(encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    assert lines[0] == "id,summary"
    assert lines[1:] == ["a,first", "b,second", "c,third"]


def test_atomic_write_csv_leaves_no_tmp_file(tmp_path: Path) -> None:
    path = tmp_path / "videos.csv"

    _atomic_write_csv(
        path,
        lambda writer: writer.writerow({"id": "abc", "summary": "text"}),
        fieldnames=SUMMARY_FIELDS,
    )

    assert path.exists()
    assert not path.with_suffix(".csv.tmp").exists()


def test_write_metadata_merge_updates_and_preserves_extra_rows(tmp_path: Path) -> None:
    path = tmp_path / "videos.csv"
    write_metadata([_video_row("a", "A"), _video_row("b", "B")], path)
    write_metadata(
        [_video_row("b", "B-updated"), _video_row("c", "C")],
        path,
        merge=True,
    )

    rows = read_metadata(path)
    assert [row["id"] for row in rows] == ["b", "c", "a"]
    assert rows[0]["title"] == "B-updated"
    assert rows[2]["title"] == "A"


def test_merge_videos_and_summaries_joins_on_id(tmp_path: Path) -> None:
    videos_path = tmp_path / "videos.csv"
    summaries_path = tmp_path / "summaries.csv"
    write_metadata(
        [
            _video_row("a", "A"),
            _video_row("b", "B"),
        ],
        videos_path,
    )
    write_summaries({"a": "summary a"}, summaries_path)

    rows = merge_videos_and_summaries(videos_path, summaries_path)
    assert [row["id"] for row in rows] == ["a", "b"]
    assert rows[0]["summary"] == "summary a"
    assert rows[1]["summary"] == ""


def test_write_combined_csv_writes_all_fields(tmp_path: Path) -> None:
    output_path = tmp_path / "combined.csv"
    row = _video_row("a", "A")
    row["summary"] = "text"
    written = write_combined_csv([row], output_path)
    assert written == 1
    assert output_path.exists()
    assert not output_path.with_suffix(".csv.tmp").exists()


def test_failed_ids_record_clear_and_read(tmp_path: Path) -> None:
    path = tmp_path / "failed_ids.txt"
    record_failed_id("vid1", path)
    record_failed_id("vid2", path)
    record_failed_id("vid1", path)
    assert read_failed_ids(path) == ["vid1", "vid2"]

    clear_failed_id("vid1", path)
    assert read_failed_ids(path) == ["vid2"]

    clear_failed_id("vid2", path)
    assert read_failed_ids(path) == []
    assert not path.exists()
