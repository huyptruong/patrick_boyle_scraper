"""Scrape YouTube channel metadata into videos.csv."""

from __future__ import annotations

import argparse
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from scraper.config import VIDEO_FIELDS, VIDEOS_CSV
from scraper.csv_io import write_metadata


# ---------------------------------------------------------------------------
# Channel metadata scraping
# ---------------------------------------------------------------------------

CHANNEL_URL = "https://www.youtube.com/@PBoyle"


def list_channel_videos(channel_url: str, max_videos: int | None) -> list[dict]:
    """List video entries (id + title) from a channel /videos tab."""
    playlist_url = f"{channel_url.rstrip('/')}/videos"
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    list_opts = {**ydl_opts, "extract_flat": "in_playlist"}
    if max_videos is not None:
        list_opts["playlistend"] = max_videos
        print(f"  1. Listing up to {max_videos} videos from {channel_url}...", flush=True)
    else:
        print(f"  1. Listing all videos from {channel_url}...", flush=True)

    try:
        with YoutubeDL(list_opts) as ydl:
            playlist = ydl.extract_info(playlist_url, download=False)
    except DownloadError as exc:
        raise RuntimeError(
            "Could not fetch channel. Check URL and network."
        ) from exc

    video_entries = [
        entry
        for entry in (playlist.get("entries") or [])
        if entry and entry.get("id")
    ]
    print(f"  Found {len(video_entries)} videos.", flush=True)
    return video_entries


def scrape_metadata(
    channel_url: str,
    max_videos: int | None,
    *,
    stop_on_error: bool = False,
) -> tuple[list[dict], int, int]:
    """Return metadata rows plus fetch stats for a YouTube channel.

    1. List video ids from the channel /videos tab (fast, titles only).
    2. For each id, fetch full metadata with yt-dlp.

    Returns (rows, total_listed, skipped_count).
    """
    video_entries = list_channel_videos(channel_url, max_videos)
    total = len(video_entries)
    skipped_count = 0

    # 2. Fetch full metadata for each video
    print("  2. Fetching metadata...", flush=True)
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    rows = []
    with YoutubeDL(ydl_opts) as ydl:
        for index, entry in enumerate(video_entries, start=1):
            video_id = entry["id"]
            url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
            title = entry.get("title") or url
            print(f"    [{index}/{total}] {title}", flush=True)
            try:
                info = ydl.extract_info(url, download=False)
            except DownloadError as exc:
                if stop_on_error:
                    raise RuntimeError(
                        f"Could not fetch video metadata for {video_id}. "
                        "Check URL and network."
                    ) from exc
                print(f"    Skipped {video_id}: {exc}", flush=True)
                skipped_count += 1
                continue
            rows.append({field: info.get(field) for field in VIDEO_FIELDS})

    return rows, total, skipped_count


# ---------------------------------------------------------------------------
# Run scraper
# ---------------------------------------------------------------------------


def main() -> None:
    """Scrape channel metadata and write videos.csv.

    Usage:
        python scrape_metadata.py
            All videos from @PBoyle → data/videos.csv

        python scrape_metadata.py --max-videos 10
            Only the 10 newest videos (test run)

        python scrape_metadata.py --dry-run --max-videos 10
            List videos without fetching metadata or writing CSV

        python scrape_metadata.py --merge --max-videos 10
            Refresh 10 newest videos without removing older rows in videos.csv

        python scrape_metadata.py --stop-on-error
            Stop on the first failed video (default: skip and continue)

        python scrape_metadata.py --channel URL --output path.csv
            Different channel or output file
    """
    parser = argparse.ArgumentParser(
        description="Scrape YouTube channel metadata into data/videos.csv",
    )
    parser.add_argument(
        "--channel",
        default=CHANNEL_URL,
        help="YouTube channel URL (default: @PBoyle)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=VIDEOS_CSV,
        help="Output CSV path (default: data/videos.csv)",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="Limit to N newest videos (default: all on channel)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List videos only; do not fetch metadata or write CSV",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge into existing CSV instead of replacing it",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop on the first failed video (default: skip and continue)",
    )
    args = parser.parse_args()

    if args.max_videos is not None and args.max_videos <= 0:
        raise ValueError("--max-videos must be a positive integer")

    if args.dry_run:
        video_entries = list_channel_videos(args.channel, args.max_videos)
        print("Dry run — no metadata will be fetched or written.", flush=True)
        for index, entry in enumerate(video_entries, start=1):
            video_id = entry["id"]
            title = entry.get("title") or video_id
            print(f"  [{index}/{len(video_entries)}] {title} ({video_id})", flush=True)
        merge_note = " (merge mode)" if args.merge else ""
        print(f"Would scrape {len(video_entries)} videos to {args.output}{merge_note}", flush=True)
        return

    rows, total, skipped_count = scrape_metadata(
        args.channel,
        args.max_videos,
        stop_on_error=args.stop_on_error,
    )
    written_count = write_metadata(rows, args.output, merge=args.merge)
    print(
        f"Fetched {len(rows)} of {total} videos ({skipped_count} skipped). "
        f"Wrote {written_count} metadata rows to {args.output}"
        + (" (merged)" if args.merge else ""),
        flush=True,
    )


if __name__ == "__main__":
    main()
