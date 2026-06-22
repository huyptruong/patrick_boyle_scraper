"""Brave UI automation for extracting one video summary.

Production code calls ``extract_summary``; tests call ``extract_one_summary`` with
``fake_actions()`` so Brave never opens.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any

import pyautogui
import pyperclip

from scraper.config import BRAVE_APP_NAME, IS_MAC, IS_WINDOWS, WINDOWS_BRAVE_EXE

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
# Real Brave launch / quit
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
        pyautogui.hotkey("win", "up")
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
# Extract one summary (seam: pass real or fake actions)
# ---------------------------------------------------------------------------

BrowserActions = dict[str, Any]


def extract_one_summary(
    video_url: str,
    click_positions: dict[str, list[int]],
    actions: BrowserActions,
) -> str:
    """Run the 10-step Brave extract procedure; return copied summary text."""
    if IS_MAC:
        modifier = "command"
    elif IS_WINDOWS:
        modifier = "ctrl"
    else:
        modifier = "command"

    try:
        print("  1. Opening Brave...", flush=True)
        actions["start_brave"]()

        print("  2. Clicking address bar...", flush=True)
        actions["click"](*click_positions["address_bar_click"])
        actions["wait"]("after_click")

        print(f"  3. Navigating to the video: {video_url}", flush=True)
        actions["clipboard_copy"](video_url)
        actions["hotkey"](modifier, "a")
        actions["hotkey"](modifier, "v")
        actions["press"]("enter")
        actions["wait"]("after_navigate")

        print("  4. Clicking Pause...", flush=True)
        actions["click"](*click_positions["pause_button_click"])
        actions["wait"]("after_click")

        print("  5. Clicking Ask...", flush=True)
        actions["click"](*click_positions["ask_button_click"])
        actions["wait"]("after_ask")

        print("  6. Clicking Summarize the video...", flush=True)
        actions["click"](*click_positions["summarize_button_click"])
        actions["wait"]("after_summarize")

        print("  7. Clicking inside summary box...", flush=True)
        actions["click"](*click_positions["summary_box_click"])
        actions["wait"]("after_click")

        print(f"  8. Scrolling in summary box ({modifier}+Down)...", flush=True)
        actions["hotkey"](modifier, "down")
        actions["wait"]("after_click")

        print("  9. Clicking Copy...", flush=True)
        return _copy_summary_text(click_positions, actions)
    finally:
        print("  10. Quitting Brave...", flush=True)
        actions["quit_brave"]()


def _copy_summary_text(
    click_positions: dict[str, list[int]],
    actions: BrowserActions,
) -> str:
    """Click Copy and read the clipboard; retry once if empty."""
    actions["click"](*click_positions["copy_button_click"])
    actions["wait"]("after_copy")
    summary = actions["clipboard_paste"]().strip()
    if summary:
        return summary

    print("  9b. Copy was empty — waiting and retrying...", flush=True)
    actions["wait"]("copy_retry_wait")
    actions["click"](*click_positions["copy_button_click"])
    actions["wait"]("after_copy")
    summary = actions["clipboard_paste"]().strip()
    if not summary:
        raise RuntimeError(
            "Copy returned empty text. The summary may not have loaded yet — "
            "try increasing EXTRACT_WAITS in scraper/brave_extract.py or use --slow."
        )
    return summary


def real_actions() -> BrowserActions:
    """Production bundle: real Brave, pyautogui, and clipboard."""
    return {
        "start_brave": start_brave,
        "quit_brave": quit_brave,
        "click": pyautogui.click,
        "hotkey": pyautogui.hotkey,
        "press": pyautogui.press,
        "clipboard_copy": pyperclip.copy,
        "clipboard_paste": pyperclip.paste,
        "wait": _wait,
    }


def fake_actions(
    *,
    summary_text: str = "Test summary from fake browser",
    empty_first_paste: bool = False,
) -> BrowserActions:
    """Test bundle: record calls, no Brave, no sleeps."""
    calls: list[tuple[str, ...]] = []
    paste_attempts = 0

    def record(name: str, *args: object) -> None:
        calls.append((name, *args))

    def clipboard_paste() -> str:
        nonlocal paste_attempts
        paste_attempts += 1
        record("clipboard_paste")
        if empty_first_paste and paste_attempts == 1:
            return ""
        return summary_text

    return {
        "start_brave": lambda: record("start_brave"),
        "quit_brave": lambda: record("quit_brave"),
        "click": lambda *coords: record("click", *coords),
        "hotkey": lambda *keys: record("hotkey", *keys),
        "press": lambda key: record("press", key),
        "clipboard_copy": lambda text: record("clipboard_copy", text),
        "clipboard_paste": clipboard_paste,
        "wait": lambda key: record("wait", key),
        "_calls": calls,
    }


def extract_summary(
    video_url: str,
    click_positions: dict[str, list[int]],
) -> str:
    """Extract one summary using real Brave UI automation."""
    return extract_one_summary(video_url, click_positions, real_actions())
