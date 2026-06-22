"""Export videos.csv joined with summaries.csv."""

from __future__ import annotations

import argparse
from pathlib import Path

from config import VIDEOS_CSV, VIDEOS_WITH_SUMMARIES_CSV, SUMMARIES_CSV
from csv_io import merge_videos_and_summaries, write_combined_csv


def main() -> None:
    """Write data/videos_with_summaries.csv."""
    parser = argparse.ArgumentParser(
        description="Export videos.csv joined with summaries.csv on id.",
    )
    parser.add_argument("--videos", type=Path, default=VIDEOS_CSV)
    parser.add_argument("--summaries", type=Path, default=SUMMARIES_CSV)
    parser.add_argument("--output", type=Path, default=VIDEOS_WITH_SUMMARIES_CSV)
    args = parser.parse_args()

    rows = merge_videos_and_summaries(args.videos, args.summaries)
    written = write_combined_csv(rows, args.output)
    with_summary = sum(1 for row in rows if row.get("summary", "").strip())
    print(
        f"Wrote {written} rows to {args.output} ({with_summary} with summaries)",
        flush=True,
    )


if __name__ == "__main__":
    main()
