"""Extract video summaries via browser UI automation (Brave Ask: clicks + keyboard)."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from scraper.brave_extract import extract_summary, set_wait_multiplier
from scraper.config import SUMMARIES_CSV, VIDEOS_CSV, load_click_positions, require_system
from scraper.csv_io import (
    clear_failed_id,
    read_failed_ids,
    read_metadata,
    read_summaries,
    record_failed_id,
    write_summaries,
)
from scraper.extract_plan import count_videos_to_extract, select_metadata_rows
from scraper.run_log import log_extract_result


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes, secs = divmod(total_seconds, 60)
    if minutes:
        return f"{minutes} min {secs} sec"
    return f"{secs} sec"


def main() -> None:
    """Extract summaries via Brave UI automation into summaries.csv.

    Run ``python calibrate.py`` once per machine/monitor before your first extract.

    Usage:
        python extract_summaries.py --max-videos 1
            Extract one video (test run)

        python extract_summaries.py --skip-existing
            Skip videos that already have a summary

        python extract_summaries.py wKXgeNwNRJ4
            Re-extract one video by id (must be in videos.csv, not a URL)

        python extract_summaries.py --stop-on-error
            Stop the batch on the first failed video (default: continue)

        python extract_summaries.py --dry-run --max-videos 3
            Show which videos would run without opening Brave

        python extract_summaries.py --slow
            Double all wait times (same as --wait-multiplier 2)

        python extract_summaries.py --retry-failed
            Re-run video ids listed in data/failed_ids.txt
    """
    parser = argparse.ArgumentParser(
        description="Extract summaries via browser UI automation (Brave Ask)."
    )
    parser.add_argument(
        "video_ids",
        nargs="*",
        metavar="VIDEO_ID",
        help="YouTube video id(s) from videos.csv (not URLs; always re-runs)",
    )
    parser.add_argument("--input", type=Path, default=VIDEOS_CSV)
    parser.add_argument("--output", type=Path, default=SUMMARIES_CSV)
    parser.add_argument("--max-videos", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the batch on the first failed video (default: continue)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which videos would run without opening Brave",
    )
    parser.add_argument(
        "--wait-multiplier",
        type=float,
        default=1.0,
        help="Multiply all EXTRACT_WAITS sleeps (e.g. 2 for a slow machine)",
    )
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Same as --wait-multiplier 2",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-run video ids listed in data/failed_ids.txt",
    )
    args = parser.parse_args()

    if args.retry_failed and args.video_ids:
        raise ValueError("Use either --retry-failed or explicit VIDEO_ID args, not both")

    if args.max_videos is not None and args.max_videos <= 0:
        raise ValueError("--max-videos must be a positive integer")

    wait_multiplier = 2.0 if args.slow else args.wait_multiplier
    if wait_multiplier <= 0:
        raise ValueError("--wait-multiplier must be a positive number")
    set_wait_multiplier(wait_multiplier)

    all_metadata = read_metadata(args.input)
    if not all_metadata:
        raise ValueError(f"No metadata rows in {args.input}")

    video_ids = list(args.video_ids)
    if args.retry_failed:
        video_ids = read_failed_ids()
        if not video_ids:
            print("No failed video ids in data/failed_ids.txt", flush=True)
            return

    metadata_rows = select_metadata_rows(
        all_metadata,
        video_ids=video_ids,
        max_videos=args.max_videos,
        input_path=args.input,
    )

    summaries = read_summaries(args.output)
    explicit_video_ids = bool(video_ids)

    if args.dry_run:
        would_extract: list[tuple[str, str]] = []
        would_skip: list[tuple[str, str]] = []
        for row in metadata_rows:
            vid = row["id"]
            title = row.get("title", vid)
            if (
                args.skip_existing
                and not explicit_video_ids
                and summaries.get(vid, "").strip()
            ):
                would_skip.append((vid, title))
            else:
                would_extract.append((vid, title))

        print("Dry run — no videos will be extracted.", flush=True)
        for vid, title in would_extract:
            print(f"  Would extract: {title} ({vid})", flush=True)
        for vid, title in would_skip:
            print(f"  Would skip: {title} ({vid})", flush=True)
        print(
            f"Would extract {len(would_extract)}, skip {len(would_skip)} "
            f"(of {len(metadata_rows)} selected)",
            flush=True,
        )
        return

    require_system()
    click_positions = load_click_positions()
    video_order = [row["id"] for row in all_metadata]
    extracted_count = 0
    failed_count = 0
    to_extract = count_videos_to_extract(
        metadata_rows,
        summaries,
        skip_existing=args.skip_existing,
        explicit_video_ids=explicit_video_ids,
    )
    completed_attempts = 0
    total_elapsed = 0.0

    for index, row in enumerate(metadata_rows, start=1):
        vid = row["id"]
        title = row.get("title", vid)

        if (
            args.skip_existing
            and not explicit_video_ids
            and summaries.get(vid, "").strip()
        ):
            print(f"[{index}/{len(metadata_rows)}] Skipping: {title}", flush=True)
            continue

        if completed_attempts > 0 and to_extract > completed_attempts:
            remaining = to_extract - completed_attempts
            avg_seconds = total_elapsed / completed_attempts
            print(
                f"  ~{_format_duration(avg_seconds * remaining)} remaining "
                f"({completed_attempts}/{to_extract} done)",
                flush=True,
            )

        print(f"[{index}/{len(metadata_rows)}] Extracting summary: {title}", flush=True)
        video_url = row.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}"
        summary = None
        last_error: Exception | None = None
        attempt_started = time.monotonic()
        for attempt in range(1, 3):
            try:
                summary = extract_summary(video_url, click_positions)
                break
            except RuntimeError as exc:
                last_error = exc
                if attempt < 2:
                    print("  Retrying extract (empty summary)...", flush=True)
                    continue
            except Exception as exc:
                last_error = exc
                break

        completed_attempts += 1
        total_elapsed += time.monotonic() - attempt_started

        if summary is None:
            print(f"  Failed: {last_error}", flush=True)
            record_failed_id(vid)
            log_extract_result(vid, "failed", detail=str(last_error))
            failed_count += 1
            if args.stop_on_error:
                raise last_error
            continue

        write_summaries({vid: summary}, args.output, video_order=video_order)
        summaries[vid] = summary
        clear_failed_id(vid)
        log_extract_result(vid, "success", detail=f"{len(summary)} chars")
        extracted_count += 1
        print(f"  Saved summary ({len(summary)} chars)", flush=True)

    if extracted_count == 0:
        print(f"No summaries updated. {len(summaries)} total in {args.output}", flush=True)
    else:
        label = "summary" if extracted_count == 1 else "summaries"
        print(
            f"Extracted {extracted_count} {label}. {len(summaries)} total in {args.output}",
            flush=True,
        )
    if failed_count:
        label = "failure" if failed_count == 1 else "failures"
        print(f"{failed_count} {label} (see messages above)", flush=True)


if __name__ == "__main__":
    main()
