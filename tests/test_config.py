"""Tests for config paths."""

from __future__ import annotations

from pathlib import Path

from scraper.config import (
    DATA_DIR,
    FAILED_IDS_PATH,
    PROJECT_ROOT,
    PUBLISH_DIR,
    PUBLISH_LAST_UPDATED_JSON,
    PUBLISH_VIDEOS_CSV,
    RUN_LOG_PATH,
    SUMMARIES_CSV,
    VIDEOS_CSV,
    VIDEOS_WITH_SUMMARIES_CSV,
)


def test_data_paths_are_under_project_root() -> None:
    assert PROJECT_ROOT == Path(__file__).resolve().parent.parent
    assert DATA_DIR == PROJECT_ROOT / "data"
    assert VIDEOS_CSV == DATA_DIR / "videos.csv"
    assert SUMMARIES_CSV == DATA_DIR / "summaries.csv"
    assert VIDEOS_WITH_SUMMARIES_CSV == DATA_DIR / "videos_with_summaries.csv"
    assert RUN_LOG_PATH == DATA_DIR / "run.log"
    assert FAILED_IDS_PATH == DATA_DIR / "failed_ids.txt"
    assert PUBLISH_DIR == PROJECT_ROOT / "publish"
    assert PUBLISH_VIDEOS_CSV == PUBLISH_DIR / "videos_with_summaries.csv"
    assert PUBLISH_LAST_UPDATED_JSON == PUBLISH_DIR / "last_updated.json"
