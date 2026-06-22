"""Tests for dashboard publish pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from scraper.csv_io import write_metadata, write_summaries
from scraper.publish import publish_dashboard_data, summary_status_counts
from scraper.summary_status import summary_status
from tests.test_csv_io import _video_row


def test_summary_status_counts(tmp_path: Path) -> None:
    videos_path = tmp_path / "videos.csv"
    summaries_path = tmp_path / "summaries.csv"
    write_metadata(
        [
            _video_row("a"),
            _video_row("b"),
            _video_row("c"),
        ],
        videos_path,
    )
    write_summaries(
        {
            "a": "Real summary text.",
            "b": "https://www.youtube.com/watch?v=b",
        },
        summaries_path,
    )

    from scraper.csv_io import merge_videos_and_summaries

    rows = merge_videos_and_summaries(videos_path, summaries_path)
    counts = summary_status_counts(rows)
    assert counts == {"complete": 1, "pending": 1, "missing": 1}


def test_publish_dashboard_data_writes_csv_and_json(tmp_path: Path) -> None:
    videos_path = tmp_path / "videos.csv"
    summaries_path = tmp_path / "summaries.csv"
    publish_csv = tmp_path / "publish" / "videos_with_summaries.csv"
    publish_json = tmp_path / "publish" / "last_updated.json"

    write_metadata([_video_row("a"), _video_row("b")], videos_path)
    write_summaries(
        {
            "a": "Summary A",
            "b": "https://www.youtube.com/watch?v=b",
        },
        summaries_path,
    )

    result = publish_dashboard_data(
        videos_path,
        summaries_path,
        publish_videos_csv=publish_csv,
        publish_last_updated_json=publish_json,
        published_at="2026-06-22T12:00:00+00:00",
    )

    assert publish_csv.exists()
    assert publish_json.exists()
    assert result.video_count == 2
    assert result.summary_complete == 1
    assert result.summary_pending == 1
    assert result.summary_missing == 0

    payload = json.loads(publish_json.read_text(encoding="utf-8"))
    assert payload == {
        "published_at": "2026-06-22T12:00:00+00:00",
        "video_count": 2,
        "summary_complete": 1,
        "summary_pending": 1,
        "summary_missing": 0,
    }

    csv_text = publish_csv.read_text(encoding="utf-8")
    assert "Summary A" in csv_text
    assert summary_status("https://www.youtube.com/watch?v=b") == "pending"
