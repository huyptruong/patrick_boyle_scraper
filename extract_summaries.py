"""Extract video summaries via browser UI automation (Brave Ask: clicks + keyboard)."""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

import pyautogui
import pyperclip

from config import (
    BRAVE_APP_NAME,
    IS_MAC,
    IS_WINDOWS,
    SUMMARIES_CSV,
    VIDEOS_CSV,
    WINDOWS_BRAVE_EXE,
    load_click_positions,
    require_system,
)
from csv_io import (
    clear_failed_id,
    read_failed_ids,
    read_metadata,
    read_summaries,
    record_failed_id,
    write_summaries,
)
from run_log import log_extract_result

pyautogui.FAILSAFE = True

# Tune these if extraction fails on a slow machine or network.
EXTRACT_WAITS = {
    "brave_launch_mac": 5,
    "brave_launch_windows": 4,
    "brave_activate": 0.5,
    "brave_maximize": 1,
    "brave_focus": 0.5,
    "brave_settle": 2,
    "after_click": 1,
    "after_navigate": 5,
    "after_ask": 5,
    "after_summarize": 10,
    "copy_scroll_count": 4,
    "after_copy_scroll": 0.25,
    "after_copy": 1.5,
    "copy_retry_wait": 3,
    "quit_brave": 2,
}

_wait_multiplier = 1.0


def set_wait_multiplier(multiplier: float) -> None:
    global _wait_multiplier
    _wait_multiplier = multiplier


def _wait(key: str) -> None:
    seconds = EXTRACT_WAITS[key] * _wait_multiplier
    if seconds > 0:
        time.sleep(seconds)


# ---------------------------------------------------------------------------
# Start / quit Brave
# ---------------------------------------------------------------------------


def start_brave() -> None:
    """Launch Brave maximized, bring it to the front, and wait until it's ready."""
    if IS_MAC:
        subprocess.run(
            ["open", "-a", BRAVE_APP_NAME, "--args", "--start-maximized"],
            check=True,
        )
        _wait("brave_launch_mac")
        subprocess.run(
            ["osascript", "-e", f'tell application "{BRAVE_APP_NAME}" to activate'],
            check=False,
        )
        _wait("brave_activate")
    elif IS_WINDOWS:
        subprocess.Popen([str(WINDOWS_BRAVE_EXE), "--start-maximized"])
        _wait("brave_launch_windows")
        pyautogui.hotkey("win", "up")  # Use shortcut to maximize if --start-maximized is ignored
        _wait("brave_maximize")
        _focus_brave()

    _wait("brave_settle")


def _focus_brave() -> None:
    """Bring Brave to the front on Windows."""
    try:
        import pygetwindow as gw
    except ImportError:
        return

    for window in gw.getAllWindows():
        if window.title and "Brave" in window.title:
            window.activate()
            _wait("brave_focus")
            return


def quit_brave() -> None:
    """Quit Brave by app/process name."""
    if IS_MAC:
        subprocess.run(
            ["osascript", "-e", f'tell application "{BRAVE_APP_NAME}" to quit'],
            check=False,
        )
    elif IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/IM", "brave.exe"],
            capture_output=True,
            text=True,
        )
    _wait("quit_brave")


# ---------------------------------------------------------------------------
# Extract one summary
# ---------------------------------------------------------------------------


def extract_summary(
    video_url: str,
    click_positions: dict[str, list[int]],
) -> str:
    """Brave UI automation for one video (steps 1–10); return copied summary text."""
    # Map function keys based on platform
    if IS_MAC:
        modifier = "command"
    elif IS_WINDOWS:
        modifier = "ctrl"
    
    # Main steps to extract a video summary
    try:
        print("  1. Opening Brave...", flush=True)
        start_brave()

        print("  2. Clicking address bar...", flush=True)
        pyautogui.click(*click_positions["address_bar_click"])
        _wait("after_click")

        print(f"  3. Navigating to the video: {video_url}", flush=True)
        pyperclip.copy(video_url)
        pyautogui.hotkey(modifier, "a")
        pyautogui.hotkey(modifier, "v")
        pyautogui.press("enter")
        _wait("after_navigate")

        print("  4. Clicking Pause...", flush=True)
        pyautogui.click(*click_positions["pause_button_click"])
        _wait("after_click")

        print("  5. Clicking Ask...", flush=True)
        pyautogui.click(*click_positions["ask_button_click"])
        _wait("after_ask")

        print("  6. Clicking Summarize the video...", flush=True)
        pyautogui.click(*click_positions["summarize_button_click"])
        _wait("after_summarize")

        print("  7. Clicking inside summary box...", flush=True)
        pyautogui.click(*click_positions["summary_box_click"])
        _wait("after_click")

        scroll_count = int(EXTRACT_WAITS["copy_scroll_count"])
        print(
            f"  8. Scrolling to bottom ({modifier}+Down x{scroll_count})...",
            flush=True,
        )
        for _ in range(scroll_count):
            pyautogui.hotkey(modifier, "down")
            _wait("after_copy_scroll")

        print("  9. Clicking Copy...", flush=True)
        summary = _copy_summary_text(click_positions)

        return summary
    finally:
        print("  10. Quitting Brave...", flush=True)
        quit_brave()


def _copy_summary_text(click_positions: dict[str, list[int]]) -> str:
    """Click Copy and read the clipboard; retry once if empty."""
    pyautogui.click(*click_positions["copy_button_click"])
    _wait("after_copy")
    summary = pyperclip.paste().strip()
    if summary:
        return summary

    print("  9b. Copy was empty — waiting and retrying...", flush=True)
    _wait("copy_retry_wait")
    pyautogui.click(*click_positions["copy_button_click"])
    _wait("after_copy")
    summary = pyperclip.paste().strip()
    if not summary:
        raise RuntimeError(
            "Copy returned empty text. The summary may not have loaded yet — "
            "try increasing EXTRACT_WAITS in extract_summaries.py or use --slow."
        )
    return summary


# ---------------------------------------------------------------------------
# Run extractor
# ---------------------------------------------------------------------------


def _select_metadata_rows(
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


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes, secs = divmod(total_seconds, 60)
    if minutes:
        return f"{minutes} min {secs} sec"
    return f"{secs} sec"


def _count_videos_to_extract(
    metadata_rows: list[dict[str, str]],
    summaries: dict[str, str],
    *,
    skip_existing: bool,
    explicit_video_ids: bool,
) -> int:
    count = 0
    for row in metadata_rows:
        vid = row["id"]
        if skip_existing and not explicit_video_ids and summaries.get(vid, "").strip():
            continue
        count += 1
    return count


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

    metadata_rows = _select_metadata_rows(
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
    to_extract = _count_videos_to_extract(
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
