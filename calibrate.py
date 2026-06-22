"""One-time Brave click-position calibration for the Patrick Boyle scraper.

Run ``python calibrate.py`` once per machine/monitor before extracting summaries.
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING, Any

from config import (
    CLICK_POSITION_KEYS,
    CLICK_POSITIONS_PATH,
    SAMPLE_CALIBRATION_VIDEO,
    click_calibration_is_complete,
    require_data_files,
    require_system,
)

if TYPE_CHECKING:
    import tkinter as tk


CAPTURE_COUNTDOWN_SECONDS = 10
HUD_WIDTH = 420
HUD_MIN_HEIGHT = 120

_pyautogui_module = None

CALIBRATION_STEPS = (
    (
        1,
        "address_bar_click",
        "Address bar",
        (
            "Open Brave and maximize the window.",
            "In Brave settings, turn off Continue where you left off.",
            "Sign into YouTube if needed.",
        ),
    ),
    (
        2,
        "pause_button_click",
        "Pause button",
        (
            "Paste this sample video into the address bar and press Enter there:",
            f"  {SAMPLE_CALIBRATION_VIDEO}",
            "Leave the video playing (do not pause yet).",
        ),
    ),
    (
        3,
        "ask_button_click",
        "Ask button",
        ("Pause the video.",),
    ),
    (
        4,
        "summarize_button_click",
        "Summarize button",
        (
            "Click Ask to open the panel.",
            "Wait until you see Summarize the video.",
        ),
    ),
    (
        5,
        "summary_box_click",
        "Summary text area",
        ("Click Summarize and wait for text to appear.",),
    ),
    (
        6,
        "copy_button_click",
        "Copy button",
        (
            "Click inside the summary box.",
            "Scroll down if Copy is not visible.",
        ),
    ),
)


def require_click_calibration(*, recalibrate: bool = False) -> bool:
    """Guide users through recording click positions on a YouTube page in Brave.

    Returns True if calibration ran, False if already complete and skipped.
    """
    print("  Checking click calibration...", flush=True)
    _require_click_positions_json()

    with CLICK_POSITIONS_PATH.open(encoding="utf-8") as handle:
        positions = json.load(handle)

    if not recalibrate and click_calibration_is_complete(positions):
        print(
            f"  Calibration already complete in {CLICK_POSITIONS_PATH}.\n"
            "  Run with --recalibrate to record positions again.",
            flush=True,
        )
        return False

    print("  Starting calibration (six steps)...", flush=True)
    print(
        "\n"
        "Open Brave, maximize it, and keep one window for all steps.\n"
        f"Sample video (steps 2–6): {SAMPLE_CALIBRATION_VIDEO}\n"
        "Each step: follow the corner HUD (instructions, then Start when ready).\n"
        "On macOS, grant Accessibility to Terminal/Cursor if capture fails.\n",
        flush=True,
    )

    _require_pyautogui()
    tk = _require_tkinter()

    root = tk.Tk()
    root.withdraw()

    for step_number, position_key, label, prep_lines in CALIBRATION_STEPS:
        _calibrate_one_step(
            tk,
            root,
            positions,
            step_number,
            position_key,
            label,
            *prep_lines,
        )

    _InfoHud(
        tk,
        root,
        "Calibration complete",
        "All six click positions are saved.\n\nClose Brave when you're done.",
    ).run()

    root.destroy()
    return True


def _write_click_positions(positions: dict) -> None:
    with CLICK_POSITIONS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(positions, handle, indent=2)
        handle.write("\n")


def _require_click_positions_json() -> None:
    if CLICK_POSITIONS_PATH.exists():
        return
    CLICK_POSITIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_click_positions({key: None for key in CLICK_POSITION_KEYS})
    print(f"  Created {CLICK_POSITIONS_PATH}", flush=True)


def _calibrate_one_step(
    tk: Any,
    root: tk.Tk,
    positions: dict,
    step_number: int,
    position_key: str,
    label: str,
    *prep_lines: str,
) -> None:
    """One calibration step: show HUD, save coordinates to click_positions.json."""
    print(f"[{step_number}/6] {label} — follow the corner HUD.", flush=True)

    x, y = _CaptureHud(tk, root, step_number, label, prep_lines).run()
    positions[position_key] = [x, y]
    _write_click_positions(positions)
    print(f"  Saved {label.lower()}: [{x}, {y}]", flush=True)
    print(flush=True)


def _require_pyautogui() -> None:
    global _pyautogui_module
    try:
        import pyautogui as _pyautogui_module
    except ImportError as exc:
        raise SystemExit(
            "calibrate.py needs pyautogui to record mouse position.\n"
            "Install project dependencies:\n"
            "  pip install -r requirements.txt"
        ) from exc


def _require_tkinter() -> Any:
    try:
        import tkinter as tk
    except ImportError as exc:
        raise SystemExit(
            "calibrate.py needs tkinter for the countdown HUD.\n"
            "On macOS with Homebrew Python, install it:\n"
            "  brew install python-tk@3.12\n"
            "(Match your Python version — run: python --version)"
        ) from exc
    return tk


class _CaptureHud:
    """Small corner window for one calibration step."""

    def __init__(
        self,
        tk: Any,
        root: tk.Tk,
        step_number: int,
        label: str,
        prep_lines: tuple[str, ...],
    ) -> None:
        self._root = root
        self._label = label
        self._header = f"Step {step_number}/6 · {label}"
        self._prep_text = "\n".join(prep_lines)

        self._captured: list[int] | None = None
        self._cancelled = False
        self._countdown_after_id: str | None = None

        self._hud = tk.Toplevel(root)
        self._hud.title("Calibration")
        self._hud.resizable(False, False)

        self._status = tk.Label(
            self._hud,
            justify="left",
            wraplength=HUD_WIDTH - 32,
            anchor="nw",
        )
        self._status.pack(padx=16, pady=(12, 8), fill="both", expand=True)

        self._button_row = tk.Frame(self._hud)
        self._button_row.pack(pady=(0, 12))

        self._show_prep()
        self._place_hud()

        start_button = tk.Button(
            self._button_row, text="Start", command=self.begin_countdown, width=10
        )
        start_button.pack()

        self._hud.bind("<Escape>", self.cancel_capture)
        self._hud.bind("<Return>", self.begin_countdown)
        self._hud.protocol("WM_DELETE_WINDOW", self.cancel_capture)
        self._hud.attributes("-topmost", True)
        self._hud.lift()

    def _place_hud(self) -> None:
        self._hud.update_idletasks()
        height = max(HUD_MIN_HEIGHT, self._hud.winfo_reqheight() + 12)
        max_height = max(HUD_MIN_HEIGHT, self._hud.winfo_screenheight() - 48)
        height = min(height, max_height)
        x = max(0, self._hud.winfo_screenwidth() - HUD_WIDTH - 24)
        y = 24
        self._hud.geometry(f"{HUD_WIDTH}x{height}+{x}+{y}")

    def _show_prep(self) -> None:
        self._status.config(
            text=(
                f"{self._header}\n\n"
                f"{self._prep_text}\n\n"
                f"When ready, click Start, then hover over {self._label}."
            )
        )

    def _show_countdown(self, remaining: int) -> None:
        self._status.config(
            text=(
                f"{self._header}\n"
                f"Hover over: {self._label}\n"
                f"(Do not click.)\n\n"
                f"Saving in {remaining}…"
            )
        )
        self._place_hud()

    def cancel_capture(self, _event: object | None = None) -> None:
        self._cancelled = True
        if self._countdown_after_id is not None:
            self._hud.after_cancel(self._countdown_after_id)
        self._countdown_after_id = None
        self._hud.destroy()

    def begin_countdown(self, _event: object | None = None) -> None:
        if self._cancelled:
            return
        self._button_row.destroy()
        self._show_countdown(CAPTURE_COUNTDOWN_SECONDS)
        self._countdown_after_id = self._hud.after(
            1000, self._on_countdown_second, CAPTURE_COUNTDOWN_SECONDS
        )

    def _on_countdown_second(self, remaining: int) -> None:
        if self._cancelled:
            return
        if remaining <= 0:
            self._captured = list(_pyautogui_module.position())
            self._hud.destroy()
            return
        self._show_countdown(remaining)
        self._countdown_after_id = self._hud.after(
            1000, self._on_countdown_second, remaining - 1
        )

    def run(self) -> list[int]:
        self._root.wait_window(self._hud)
        if self._captured is None:
            print("Calibration cancelled.", flush=True)
            raise SystemExit(1)
        return self._captured


class _InfoHud:
    """Corner popup with a message and OK button (no click capture)."""

    def __init__(
        self,
        tk: Any,
        root: tk.Tk,
        header: str,
        message: str,
    ) -> None:
        self._root = root

        self._hud = tk.Toplevel(root)
        self._hud.title("Calibration")
        self._hud.resizable(False, False)

        status = tk.Label(
            self._hud,
            text=f"{header}\n\n{message}",
            justify="left",
            wraplength=HUD_WIDTH - 32,
            anchor="nw",
        )
        status.pack(padx=16, pady=(12, 8), fill="both", expand=True)

        ok_button = tk.Button(self._hud, text="OK", command=self._hud.destroy, width=10)
        ok_button.pack(pady=(0, 12))

        self._hud.bind("<Escape>", lambda _event: self._hud.destroy())
        self._hud.bind("<Return>", lambda _event: self._hud.destroy())
        self._hud.protocol("WM_DELETE_WINDOW", self._hud.destroy)
        self._hud.attributes("-topmost", True)
        self._hud.lift()

        self._hud.update_idletasks()
        height = max(HUD_MIN_HEIGHT, self._hud.winfo_reqheight() + 12)
        max_height = max(HUD_MIN_HEIGHT, self._hud.winfo_screenheight() - 48)
        height = min(height, max_height)
        x = max(0, self._hud.winfo_screenwidth() - HUD_WIDTH - 24)
        self._hud.geometry(f"{HUD_WIDTH}x{height}+{x}+24")

    def run(self) -> None:
        self._root.wait_window(self._hud)


def main() -> None:
    """Check prerequisites, create data files, run calibration."""
    parser = argparse.ArgumentParser(
        description="Prepare data files and calibrate Brave click positions.",
    )
    parser.add_argument(
        "--recalibrate",
        action="store_true",
        help="Re-run all six calibration steps even if click_positions.json is complete",
    )
    args = parser.parse_args()

    print("Patrick Boyle scraper calibration", flush=True)
    require_system()
    require_data_files()
    calibration_ran = require_click_calibration(recalibrate=args.recalibrate)
    if calibration_ran:
        print(
            f"Calibration complete. All six click positions saved to {CLICK_POSITIONS_PATH}",
            flush=True,
        )
    else:
        print("Calibration complete. Click positions were already up to date.", flush=True)


if __name__ == "__main__":
    main()
