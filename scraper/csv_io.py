"""Read and write project CSVs. Paths and column names come from config."""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

from scraper.config import (
    COMBINED_FIELDS,
    FAILED_IDS_PATH,
    SUMMARIES_CSV,
    SUMMARY_FIELDS,
    VIDEO_FIELDS,
    VIDEOS_CSV,
    VIDEOS_WITH_SUMMARIES_CSV,
)


# ---------------------------------------------------------------------------
# Video metadata (videos.csv)
# ---------------------------------------------------------------------------


def read_metadata(csv_path: Path = VIDEOS_CSV) -> list[dict[str, str]]:
    """Read all metadata rows from videos.csv."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Run scrape_metadata.py first."
        )

    with csv_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_metadata(
    rows: list[dict],
    csv_path: Path = VIDEOS_CSV,
    *,
    fieldnames: tuple[str, ...] = VIDEO_FIELDS,
    merge: bool = False,
) -> int:
    """Write videos.csv.

    Default: replace the entire file with rows.
    merge=True: update matching ids, append new ones, keep scrape order first,
    then any existing rows not in this scrape.

    Returns the number of rows written.
    """
    if merge and csv_path.exists():
        existing = {row["id"]: row for row in read_metadata(csv_path)}
        for row in rows:
            existing[row["id"]] = row
        scraped_ids = [row["id"] for row in rows]
        extra_ids = [video_id for video_id in existing if video_id not in scraped_ids]
        rows = [existing[video_id] for video_id in scraped_ids + extra_ids]

    _atomic_write_csv(
        csv_path,
        lambda writer: writer.writerows(rows),
        fieldnames=fieldnames,
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Summaries (summaries.csv)
# ---------------------------------------------------------------------------


def read_summaries(csv_path: Path = SUMMARIES_CSV) -> dict[str, str]:
    """Read summaries.csv as id → summary."""
    if not csv_path.exists():
        return {}

    with csv_path.open(encoding="utf-8", newline="") as handle:
        return {
            row["id"]: row.get("summary", "")
            for row in csv.DictReader(handle)
            if row.get("id")
        }


def write_summaries(
    summaries: dict[str, str],
    csv_path: Path = SUMMARIES_CSV,
    *,
    video_order: list[str] | None = None,
    replace_all: bool = False,
) -> None:
    """Write summaries.csv.

    Default: update only the passed ids; other rows in the file are kept.
    replace_all=True: replace the entire file with summaries only (not append).
    """
    if replace_all:
        merged = dict(summaries)
    else:
        merged = read_summaries(csv_path)
        merged.update(summaries)

    if video_order:
        ordered_ids = [video_id for video_id in video_order if video_id in merged]
        extra_ids = [video_id for video_id in merged if video_id not in video_order]
        ids = ordered_ids + extra_ids
    else:
        ids = list(merged.keys())

    rows = [{"id": video_id, "summary": merged[video_id]} for video_id in ids]
    _atomic_write_csv(
        csv_path,
        lambda writer: writer.writerows(rows),
        fieldnames=SUMMARY_FIELDS,
    )


# ---------------------------------------------------------------------------
# Combined export (videos + summaries)
# ---------------------------------------------------------------------------


def merge_videos_and_summaries(
    videos_path: Path = VIDEOS_CSV,
    summaries_path: Path = SUMMARIES_CSV,
) -> list[dict[str, str]]:
    """Join videos.csv with summaries.csv on id (video order preserved)."""
    summaries = read_summaries(summaries_path)
    return [
        {**row, "summary": summaries.get(row["id"], "")}
        for row in read_metadata(videos_path)
    ]


def write_combined_csv(
    rows: list[dict[str, str]],
    csv_path: Path = VIDEOS_WITH_SUMMARIES_CSV,
) -> int:
    """Write videos_with_summaries.csv. Returns the number of rows written."""
    _atomic_write_csv(
        csv_path,
        lambda writer: writer.writerows(rows),
        fieldnames=COMBINED_FIELDS,
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Failed extract ids
# ---------------------------------------------------------------------------


def read_failed_ids(csv_path: Path = FAILED_IDS_PATH) -> list[str]:
    """Read failed video ids (one per line), preserving file order."""
    if not csv_path.exists():
        return []
    return [
        line.strip()
        for line in csv_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def record_failed_id(video_id: str, csv_path: Path = FAILED_IDS_PATH) -> None:
    """Append a video id to failed_ids.txt if not already listed."""
    ids = read_failed_ids(csv_path)
    if video_id in ids:
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{video_id}\n")


def clear_failed_id(video_id: str, csv_path: Path = FAILED_IDS_PATH) -> None:
    """Remove a video id from failed_ids.txt after a successful extract."""
    ids = [vid for vid in read_failed_ids(csv_path) if vid != video_id]
    if not ids:
        if csv_path.exists():
            csv_path.unlink()
        return
    csv_path.write_text("\n".join(ids) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _atomic_write_csv(
    csv_path: Path,
    write_rows: Callable[[csv.DictWriter], None],
    *,
    fieldnames: tuple[str, ...],
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = csv_path.with_suffix(f"{csv_path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        write_rows(writer)
    temp_path.replace(csv_path)
