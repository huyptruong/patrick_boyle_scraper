"""Write dashboard publish artifacts under publish/."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scraper.csv_io import merge_videos_and_summaries, write_combined_csv
from scraper.summary_status import SummaryStatus, summary_status


@dataclass(frozen=True)
class PublishResult:
    """Paths and counts from a publish run."""

    videos_csv: Path
    last_updated_json: Path
    video_count: int
    summary_complete: int
    summary_pending: int
    summary_missing: int
    published_at: str


def summary_status_counts(rows: list[dict[str, str]]) -> dict[SummaryStatus, int]:
    """Count rows by derived summary status."""
    counts: dict[SummaryStatus, int] = {
        "complete": 0,
        "pending": 0,
        "missing": 0,
    }
    for row in rows:
        counts[summary_status(row.get("summary", ""))] += 1
    return counts


def write_last_updated_json(
    path: Path,
    *,
    published_at: str,
    video_count: int,
    summary_complete: int,
    summary_pending: int,
    summary_missing: int,
) -> None:
    """Write publish/last_updated.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "published_at": published_at,
        "video_count": video_count,
        "summary_complete": summary_complete,
        "summary_pending": summary_pending,
        "summary_missing": summary_missing,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def publish_dashboard_data(
    videos_path: Path,
    summaries_path: Path,
    *,
    publish_videos_csv: Path,
    publish_last_updated_json: Path,
    published_at: str | None = None,
) -> PublishResult:
    """Join sources and write publish/ CSV + last_updated.json."""
    rows = merge_videos_and_summaries(videos_path, summaries_path)
    write_combined_csv(rows, publish_videos_csv)

    counts = summary_status_counts(rows)
    timestamp = published_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    write_last_updated_json(
        publish_last_updated_json,
        published_at=timestamp,
        video_count=len(rows),
        summary_complete=counts["complete"],
        summary_pending=counts["pending"],
        summary_missing=counts["missing"],
    )
    return PublishResult(
        videos_csv=publish_videos_csv,
        last_updated_json=publish_last_updated_json,
        video_count=len(rows),
        summary_complete=counts["complete"],
        summary_pending=counts["pending"],
        summary_missing=counts["missing"],
        published_at=timestamp,
    )
