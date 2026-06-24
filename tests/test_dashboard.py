"""Tests for dashboard data preparation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.formatting import (
    format_duration,
    format_published_at,
    format_upload_date,
    summary_preview_text,
)
from dashboard.load_data import (
    average_views_by_month,
    load_publish_metadata,
    load_videos_dataframe,
    prepare_videos_dataframe,
    summary_coverage_by_month,
    uploads_per_month,
)
from dashboard.operator import REFRESH_STEPS, pending_videos
from scraper.publish import publish_dashboard_data
from tests.test_csv_io import _video_row
from scraper.csv_io import write_metadata, write_summaries


def test_format_helpers() -> None:
    assert format_upload_date("20260620") == "2026-06-20"
    assert format_duration("125") == "2:05"
    assert format_duration("3661") == "1:01:01"
    assert "June" in format_published_at("2026-06-22T12:00:00+00:00")
    assert summary_preview_text("Short text.", "complete") == "Short text."
    assert summary_preview_text("https://youtu.be/x", "pending") == "Summary pending"


def test_prepare_videos_dataframe_status_and_preview() -> None:
    frame = pd.DataFrame(
        [
            {
                "id": "a",
                "title": "A",
                "webpage_url": "https://www.youtube.com/watch?v=a",
                "view_count": "1000",
                "like_count": "",
                "upload_date": "20260601",
                "duration": "90",
                "description": "",
                "channel": "",
                "thumbnail": "",
                "summary": "Real summary.",
            },
            {
                "id": "b",
                "title": "B",
                "webpage_url": "https://www.youtube.com/watch?v=b",
                "view_count": "bad",
                "like_count": "",
                "upload_date": "",
                "duration": "",
                "description": "",
                "channel": "",
                "thumbnail": "",
                "summary": "https://www.youtube.com/watch?v=b",
            },
        ]
    )
    prepared = prepare_videos_dataframe(frame)
    assert prepared.loc[0, "status"] == "complete"
    assert prepared.loc[1, "status"] == "pending"
    assert prepared.loc[1, "summary_preview"] == "Summary pending"
    assert prepared.loc[0, "views"] == 1000
    assert prepared.loc[1, "views"] == 0


def test_monthly_aggregates(tmp_path: Path) -> None:
    frame = prepare_videos_dataframe(
        pd.DataFrame(
            [
                {
                    **{
                        key: ""
                        for key in (
                            "id",
                            "title",
                            "webpage_url",
                            "like_count",
                            "description",
                            "channel",
                            "thumbnail",
                        )
                    },
                    "view_count": "100",
                    "upload_date": "20260115",
                    "duration": "60",
                    "summary": "One",
                },
                {
                    **{
                        key: ""
                        for key in (
                            "id",
                            "title",
                            "webpage_url",
                            "like_count",
                            "description",
                            "channel",
                            "thumbnail",
                        )
                    },
                    "view_count": "200",
                    "upload_date": "20260120",
                    "duration": "60",
                    "summary": "https://example.com",
                },
                {
                    **{
                        key: ""
                        for key in (
                            "id",
                            "title",
                            "webpage_url",
                            "like_count",
                            "description",
                            "channel",
                            "thumbnail",
                        )
                    },
                    "view_count": "300",
                    "upload_date": "20260201",
                    "duration": "60",
                    "summary": "",
                },
            ]
        )
    )
    uploads = uploads_per_month(frame)
    coverage = summary_coverage_by_month(frame)
    averages = average_views_by_month(frame)
    assert uploads.loc["2026-01", "uploads"] == 2
    assert coverage.loc["2026-01", "complete"] == 1
    assert coverage.loc["2026-01", "pending"] == 1
    assert coverage.loc["2026-02", "missing"] == 1
    assert averages.loc["2026-01", "views"] == 150
    assert averages.loc["2026-02", "views"] == 300


def test_pending_videos_lists_only_url_placeholders() -> None:
    frame = prepare_videos_dataframe(
        pd.DataFrame(
            [
                {
                    **{key: "" for key in ("id", "title", "webpage_url", "like_count", "description", "channel", "thumbnail")},
                    "view_count": "1",
                    "upload_date": "20260101",
                    "duration": "60",
                    "summary": "Done",
                },
                {
                    **{key: "" for key in ("id", "title", "webpage_url", "like_count", "description", "channel", "thumbnail")},
                    "view_count": "1",
                    "upload_date": "20260102",
                    "duration": "60",
                    "summary": "https://www.youtube.com/watch?v=x",
                },
            ]
        )
    )
    frame.loc[0, "id"] = "a"
    frame.loc[0, "title"] = "A"
    frame.loc[0, "webpage_url"] = "https://www.youtube.com/watch?v=a"
    frame.loc[1, "id"] = "b"
    frame.loc[1, "title"] = "B"
    frame.loc[1, "webpage_url"] = "https://www.youtube.com/watch?v=b"

    pending = pending_videos(frame)
    assert len(pending) == 1
    assert pending.iloc[0]["id"] == "b"


def test_refresh_steps_include_publish_and_push() -> None:
    steps_text = " ".join(REFRESH_STEPS)
    assert "publish_data.py" in steps_text
    assert "git push" in steps_text
    assert "extract_summaries.py --skip-existing" in steps_text
    assert "review_app.py" in steps_text


def test_load_publish_files(tmp_path: Path) -> None:
    videos_path = tmp_path / "videos.csv"
    summaries_path = tmp_path / "summaries.csv"
    publish_csv = tmp_path / "publish" / "videos_with_summaries.csv"
    publish_json = tmp_path / "publish" / "last_updated.json"

    write_metadata([_video_row("a", "Video A")], videos_path)
    write_summaries({"a": "Summary text"}, summaries_path)
    publish_dashboard_data(
        videos_path,
        summaries_path,
        publish_videos_csv=publish_csv,
        publish_last_updated_json=publish_json,
        published_at="2026-06-22T12:00:00+00:00",
    )

    metadata = load_publish_metadata(publish_json)
    videos = prepare_videos_dataframe(load_videos_dataframe(publish_csv))
    assert metadata["video_count"] == 1
    assert len(videos) == 1
    assert videos.iloc[0]["summary_preview"] == "Summary text"


def test_dashboard_app_imports_like_streamlit() -> None:
    """Streamlit puts dashboard/ on sys.path; app.py must still import."""
    import importlib.util
    import sys

    root = Path(__file__).resolve().parent.parent
    dashboard_dir = str(root / "dashboard")
    saved_path = sys.path.copy()
    try:
        sys.path = [dashboard_dir, *[p for p in sys.path if p not in {dashboard_dir, str(root)}]]
        spec = importlib.util.spec_from_file_location(
            "dashboard_entry",
            root / "dashboard" / "app.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert callable(module.main)
    finally:
        sys.path[:] = saved_path
