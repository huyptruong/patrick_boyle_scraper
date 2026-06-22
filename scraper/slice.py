"""Study-slice helpers: parse YYYY-MM, filter by upload_date, merge CSV rows."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

_SLICE_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")


def parse_slice(value: str) -> tuple[str, str]:
    """Validate ``YYYY-MM`` and return ``(label, YYYYMM prefix)``."""
    match = _SLICE_PATTERN.match(value)
    if not match:
        raise ValueError(f"--slice must be YYYY-MM (got {value!r})")

    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        raise ValueError(f"--slice month must be 01–12 (got {value!r})")

    datetime(year, month, 1)
    label = f"{year:04d}-{month:02d}"
    return label, f"{year:04d}{month:02d}"


def upload_date_in_slice(upload_date: str | None, yyyymm_prefix: str) -> bool:
    """True when ``upload_date`` (``YYYYMMDD``) falls in the slice month."""
    if not upload_date or len(upload_date) < 6:
        return False
    return upload_date[:6] == yyyymm_prefix


def filter_metadata_by_slice(
    rows: list[dict[str, str]],
    yyyymm_prefix: str,
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if upload_date_in_slice(row.get("upload_date"), yyyymm_prefix)
    ]


def count_metadata_in_slice(
    rows: list[dict[str, str]],
    yyyymm_prefix: str,
) -> int:
    return len(filter_metadata_by_slice(rows, yyyymm_prefix))


def slice_summaries_exist(
    summaries: dict[str, str],
    metadata_rows: list[dict[str, str]],
    yyyymm_prefix: str,
) -> bool:
    """True if any video in the slice month has a non-empty summary."""
    for row in filter_metadata_by_slice(metadata_rows, yyyymm_prefix):
        if summaries.get(row["id"], "").strip():
            return True
    return False


def confirm_slice_refresh(
    resource_label: str,
    slice_label: str,
    count: int,
    *,
    input_fn: Callable[[str], str] = input,
) -> bool:
    """Ask whether to refresh an existing study slice. Default is no."""
    print(
        f"{slice_label} already has {count} {resource_label} in the file.",
        flush=True,
    )
    answer = input_fn(f"Refresh {slice_label}? [y/N] ").strip().lower()
    return answer in ("y", "yes")


def merge_metadata_for_slice(
    existing_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
    yyyymm_prefix: str,
    *,
    refresh: bool,
) -> list[dict[str, str]]:
    """Append or replace one month's metadata rows; other months unchanged."""
    if refresh:
        kept = [
            row
            for row in existing_rows
            if not upload_date_in_slice(row.get("upload_date"), yyyymm_prefix)
        ]
    else:
        kept = list(existing_rows)

    by_id = {row["id"]: row for row in kept}
    for row in new_rows:
        by_id[row["id"]] = row

    kept_ids = [row["id"] for row in kept]
    new_ids = [row["id"] for row in new_rows if row["id"] not in set(kept_ids)]
    return [by_id[video_id] for video_id in kept_ids + new_ids]


def should_stop_channel_scan(upload_date: str | None, yyyymm_prefix: str) -> bool:
    """Newest-first channel list: stop once we're older than the slice month."""
    if not upload_date or len(upload_date) < 6:
        return False
    return upload_date[:6] < yyyymm_prefix


def available_slice_labels(rows: list[dict[str, str]]) -> list[str]:
    """Sorted ``YYYY-MM`` labels present in metadata ``upload_date`` values."""
    months: set[str] = set()
    for row in rows:
        upload_date = row.get("upload_date")
        if upload_date and len(upload_date) >= 6:
            months.add(f"{upload_date[:4]}-{upload_date[4:6]}")
    return sorted(months, reverse=True)


def exit_missing_slice_metadata(
    slice_label: str,
    *,
    csv_path: Path,
    all_metadata: list[dict[str, str]],
) -> None:
    """Print guidance and stop when ``videos.csv`` has no rows for this slice."""
    available = available_slice_labels(all_metadata)
    print(f"No metadata for study slice {slice_label}.", flush=True)
    print(flush=True)
    print("Scrape metadata for this month before extracting summaries:", flush=True)
    print(f"  python scrape_metadata.py --slice {slice_label}", flush=True)
    if available:
        print(flush=True)
        print(f"Months already in {csv_path.name}: {', '.join(available)}", flush=True)
    sys.exit(1)
