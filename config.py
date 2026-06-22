"""Shared project settings for the Patrick Boyle scraper.

Paths, CSV columns, platform checks, and click-position validation live here.
Run ``python calibrate.py`` once per machine to record Brave click positions.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

VIDEOS_CSV = DATA_DIR / "videos.csv"
VIDEO_FIELDS = (
    "id",
    "title",
    "webpage_url",
    "view_count",
    "like_count",
    "upload_date",
    "duration",
    "description",
    "channel",
    "thumbnail",
)

SUMMARIES_CSV = DATA_DIR / "summaries.csv"
SUMMARY_FIELDS = ("id", "summary")

VIDEOS_WITH_SUMMARIES_CSV = DATA_DIR / "videos_with_summaries.csv"
COMBINED_FIELDS = VIDEO_FIELDS + ("summary",)

RUN_LOG_PATH = DATA_DIR / "run.log"
FAILED_IDS_PATH = DATA_DIR / "failed_ids.txt"

CLICK_POSITIONS_PATH = DATA_DIR / "click_positions.json"
CLICK_POSITION_KEYS = (
    "address_bar_click",
    "pause_button_click",
    "ask_button_click",
    "summarize_button_click",
    "summary_box_click",
    "copy_button_click",
)

# Sample video for calibration steps 2–6: How SpaceX Humiliated Wall Street
SAMPLE_CALIBRATION_VIDEO = "https://www.youtube.com/watch?v=wKXgeNwNRJ4"


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

BRAVE_APP_NAME = "Brave Browser"

MAC_BRAVE_APP = Path("/Applications/Brave Browser.app")
MAC_BRAVE_APP_USER = Path.home() / "Applications/Brave Browser.app"


def require_system() -> None:
    """macOS or Windows with Brave installed."""
    print("  Checking system...", flush=True)
    _require_platform()
    _require_brave_browser()


def _require_platform() -> None:
    """macOS or Windows only."""
    if not (IS_MAC or IS_WINDOWS):
        raise SystemExit(
            f"Browser UI extraction requires macOS or Windows (detected: {sys.platform})."
        )


def _require_brave_browser() -> None:
    """Brave browser must be installed in the default location for this OS."""
    _require_platform()

    if IS_MAC:
        if MAC_BRAVE_APP.is_dir() or MAC_BRAVE_APP_USER.is_dir():
            return
        raise SystemExit(
            "Brave browser is not installed. "
            "Install it from https://brave.com (expected in /Applications)."
        )

    if IS_WINDOWS:
        if WINDOWS_BRAVE_EXE.is_file():
            return
        checked = "\n".join(f"  - {path}" for path in _windows_brave_exe_candidates())
        raise SystemExit(
            "Brave Browser is not installed. "
            "Install it from https://brave.com\n"
            f"Checked:\n{checked}"
        )


def _windows_brave_exe_candidates() -> tuple[Path, ...]:
    return (
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "BraveSoftware"
        / "Brave-Browser"
        / "Application"
        / "brave.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "BraveSoftware"
        / "Brave-Browser"
        / "Application"
        / "brave.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "BraveSoftware"
        / "Brave-Browser"
        / "Application"
        / "brave.exe",
    )


def _resolve_windows_brave_exe() -> Path:
    for path in _windows_brave_exe_candidates():
        if path.is_file():
            return path
    return _windows_brave_exe_candidates()[0]


WINDOWS_BRAVE_EXE = _resolve_windows_brave_exe()


# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------


def require_data_files() -> None:
    """Create data/ and header-only CSV placeholders if they do not exist."""
    print("  Checking data files...", flush=True)
    _require_data_dir()
    _require_videos_csv()
    _require_summaries_csv()


def _require_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _require_videos_csv() -> None:
    if VIDEOS_CSV.exists():
        return
    VIDEOS_CSV.write_text(f"{','.join(VIDEO_FIELDS)}\n", encoding="utf-8")
    print(f"  Created {VIDEOS_CSV}", flush=True)


def _require_summaries_csv() -> None:
    if SUMMARIES_CSV.exists():
        return
    SUMMARIES_CSV.write_text(f"{','.join(SUMMARY_FIELDS)}\n", encoding="utf-8")
    print(f"  Created {SUMMARIES_CSV}", flush=True)


# ---------------------------------------------------------------------------
# Click positions
# ---------------------------------------------------------------------------


def is_valid_click_position(value: object) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    return all(isinstance(coord, (int, float)) for coord in value)


def click_calibration_is_complete(positions: dict) -> bool:
    return all(
        is_valid_click_position(positions.get(key)) for key in CLICK_POSITION_KEYS
    )


def load_click_positions() -> dict[str, list[int]]:
    """Load and validate click_positions.json, or exit with a plain-language message."""
    if not CLICK_POSITIONS_PATH.exists():
        raise SystemExit(
            f"{CLICK_POSITIONS_PATH} not found.\n"
            "Run calibration first:\n"
            "  python calibrate.py"
        )

    try:
        with CLICK_POSITIONS_PATH.open(encoding="utf-8") as handle:
            positions = json.load(handle)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"{CLICK_POSITIONS_PATH} is not valid JSON.\n"
            "Delete the file and run calibration again:\n"
            "  python calibrate.py"
        ) from exc

    if not isinstance(positions, dict):
        raise SystemExit(
            f"{CLICK_POSITIONS_PATH} has unexpected format.\n"
            "Delete the file and run calibration again:\n"
            "  python calibrate.py"
        )

    missing = [
        key
        for key in CLICK_POSITION_KEYS
        if not is_valid_click_position(positions.get(key))
    ]
    if missing:
        lines = "\n".join(
            f"  - Step {index}: {key.replace('_click', '').replace('_', ' ')}"
            for index, key in enumerate(CLICK_POSITION_KEYS, start=1)
            if key in missing
        )
        raise SystemExit(
            f"Click calibration is incomplete in {CLICK_POSITIONS_PATH}.\n"
            f"Missing or invalid:\n{lines}\n"
            "Run calibration:\n"
            "  python calibrate.py"
        )

    return positions
