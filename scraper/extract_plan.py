"""Decide which videos an extract run should process."""

from __future__ import annotations

from pathlib import Path


def select_metadata_rows(
    all_metadata: list[dict[str, str]],
    *,
    video_ids: list[str],
    max_videos: int | None,
    input_path: Path,
) -> list[dict[str, str]]:
    """Pick which videos to process from CLI args."""
    if video_ids:
        by_id = {row["id"]: row for row in all_metadata}
        missing = [video_id for video_id in video_ids if video_id not in by_id]
        if missing:
            raise ValueError(
                f"Video id(s) not found in {input_path}: {', '.join(missing)}"
            )
        return [by_id[video_id] for video_id in video_ids]
    if max_videos is not None:
        return all_metadata[:max_videos]
    return all_metadata


def count_videos_to_extract(
    metadata_rows: list[dict[str, str]],
    summaries: dict[str, str],
    *,
    skip_existing: bool,
    explicit_video_ids: bool,
) -> int:
    """Count how many selected videos still need extraction."""
    count = 0
    for row in metadata_rows:
        vid = row["id"]
        if skip_existing and not explicit_video_ids and summaries.get(vid, "").strip():
            continue
        count += 1
    return count
