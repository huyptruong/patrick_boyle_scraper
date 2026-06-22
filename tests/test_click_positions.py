"""Tests for click-position validation and loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
from config import CLICK_POSITION_KEYS, click_calibration_is_complete, is_valid_click_position, load_click_positions


def _valid_positions() -> dict[str, list[int]]:
    return {key: [100, 200] for key in CLICK_POSITION_KEYS}


def test_is_valid_click_position_accepts_coordinates() -> None:
    assert is_valid_click_position([100, 200])
    assert is_valid_click_position([10.5, 20.5])


@pytest.mark.parametrize(
    "value",
    [None, "bad", [100], [100, 200, 300], ["a", "b"]],
)
def test_is_valid_click_position_rejects_invalid_values(value: object) -> None:
    assert not is_valid_click_position(value)


def test_click_calibration_is_complete_requires_all_keys() -> None:
    positions = _valid_positions()
    positions["ask_button_click"] = None
    assert not click_calibration_is_complete(positions)
    assert click_calibration_is_complete(_valid_positions())


def test_load_click_positions_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "click_positions.json"
    monkeypatch.setattr(config, "CLICK_POSITIONS_PATH", missing)

    with pytest.raises(SystemExit, match="not found"):
        load_click_positions()


def test_load_click_positions_invalid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "click_positions.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(config, "CLICK_POSITIONS_PATH", path)

    with pytest.raises(SystemExit, match="not valid JSON"):
        load_click_positions()


def test_load_click_positions_incomplete_calibration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "click_positions.json"
    positions = _valid_positions()
    positions["copy_button_click"] = None
    path.write_text(json.dumps(positions), encoding="utf-8")
    monkeypatch.setattr(config, "CLICK_POSITIONS_PATH", path)

    with pytest.raises(SystemExit, match="incomplete"):
        load_click_positions()


def test_load_click_positions_returns_valid_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "click_positions.json"
    positions = _valid_positions()
    path.write_text(json.dumps(positions), encoding="utf-8")
    monkeypatch.setattr(config, "CLICK_POSITIONS_PATH", path)

    assert load_click_positions() == positions
