"""Publish dashboard-ready artifacts to publish/."""

from __future__ import annotations

import argparse
from pathlib import Path

from scraper.config import (
    PUBLISH_DIR,
    PUBLISH_LAST_UPDATED_JSON,
    PUBLISH_VIDEOS_CSV,
    SUMMARIES_CSV,
    VIDEOS_CSV,
)
from scraper.publish import publish_dashboard_data


def main() -> None:
    """Write publish/videos_with_summaries.csv and publish/last_updated.json."""
    parser = argparse.ArgumentParser(
        description="Publish videos + summaries for the Streamlit dashboard.",
    )
    parser.add_argument("--videos", type=Path, default=VIDEOS_CSV)
    parser.add_argument("--summaries", type=Path, default=SUMMARIES_CSV)
    parser.add_argument("--output-csv", type=Path, default=PUBLISH_VIDEOS_CSV)
    parser.add_argument("--output-json", type=Path, default=PUBLISH_LAST_UPDATED_JSON)
    args = parser.parse_args()

    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    result = publish_dashboard_data(
        args.videos,
        args.summaries,
        publish_videos_csv=args.output_csv,
        publish_last_updated_json=args.output_json,
    )
    print(f"Wrote {result.video_count} rows to {result.videos_csv}", flush=True)
    print(f"Wrote metadata to {result.last_updated_json}", flush=True)
    print(
        "Summary status: "
        f"{result.summary_complete} complete, "
        f"{result.summary_pending} pending, "
        f"{result.summary_missing} missing",
        flush=True,
    )
    print(
        f"Commit {PUBLISH_DIR.name}/ and push to refresh Streamlit Cloud.",
        flush=True,
    )


if __name__ == "__main__":
    main()
