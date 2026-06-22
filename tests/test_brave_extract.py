"""Tests for brave_extract using fake browser actions (no Brave)."""

from __future__ import annotations

import pytest

from scraper.brave_extract import extract_one_summary, fake_actions
from scraper.config import CLICK_POSITION_KEYS


def _click_positions() -> dict[str, list[int]]:
    return {key: [100 + index, 200 + index] for index, key in enumerate(CLICK_POSITION_KEYS)}


def test_extract_one_summary_returns_fake_text() -> None:
    actions = fake_actions(summary_text="Hello from fake browser")
    positions = _click_positions()

    result = extract_one_summary(
        "https://www.youtube.com/watch?v=abc123",
        positions,
        actions,
    )

    assert result == "Hello from fake browser"


def test_extract_one_summary_starts_and_quits_brave() -> None:
    actions = fake_actions()
    calls = actions["_calls"]

    extract_one_summary("https://www.youtube.com/watch?v=abc123", _click_positions(), actions)

    assert ("start_brave",) in calls
    assert ("quit_brave",) in calls


def test_extract_one_summary_clicks_address_bar() -> None:
    actions = fake_actions()
    positions = _click_positions()
    address = tuple(positions["address_bar_click"])

    extract_one_summary("https://www.youtube.com/watch?v=abc123", positions, actions)

    assert ("click", *address) in actions["_calls"]


def test_extract_one_summary_copies_video_url_to_clipboard() -> None:
    actions = fake_actions()
    video_url = "https://www.youtube.com/watch?v=abc123"

    extract_one_summary(video_url, _click_positions(), actions)

    assert ("clipboard_copy", video_url) in actions["_calls"]


def test_extract_one_summary_retries_empty_clipboard() -> None:
    actions = fake_actions(
        summary_text="Second try worked",
        empty_first_paste=True,
    )

    result = extract_one_summary(
        "https://www.youtube.com/watch?v=abc123",
        _click_positions(),
        actions,
    )

    assert result == "Second try worked"
    paste_calls = [call for call in actions["_calls"] if call[0] == "clipboard_paste"]
    assert len(paste_calls) == 2


def test_extract_one_summary_raises_when_clipboard_stays_empty() -> None:
    actions = fake_actions(summary_text="")
    actions["clipboard_paste"] = lambda: ""

    with pytest.raises(RuntimeError, match="Copy returned empty text"):
        extract_one_summary(
            "https://www.youtube.com/watch?v=abc123",
            _click_positions(),
            actions,
        )
