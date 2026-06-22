"""Tests for study-slice parsing and CSV merge helpers."""

from __future__ import annotations

import pytest

from scraper.slice import (
    available_slice_labels,
    confirm_slice_refresh,
    exit_missing_slice_metadata,
    filter_metadata_by_slice,
    merge_metadata_for_slice,
    parse_slice,
    should_stop_channel_scan,
    upload_date_in_slice,
)


def test_parse_slice_accepts_valid_month() -> None:
    assert parse_slice("2026-06") == ("2026-06", "202606")


@pytest.mark.parametrize(
    "value",
    ["2026-6", "26-06", "2026/06", "202606", "abcd-ef"],
)
def test_parse_slice_rejects_invalid_format(value: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM"):
        parse_slice(value)


def test_parse_slice_rejects_month_out_of_range() -> None:
    with pytest.raises(ValueError, match="01–12"):
        parse_slice("2026-13")


def test_upload_date_in_slice_matches_prefix() -> None:
    assert upload_date_in_slice("20260615", "202606")
    assert not upload_date_in_slice("20260530", "202606")
    assert not upload_date_in_slice("", "202606")


def test_filter_metadata_by_slice() -> None:
    rows = [
        {"id": "a", "upload_date": "20260601"},
        {"id": "b", "upload_date": "20260531"},
        {"id": "c", "upload_date": "20260630"},
    ]
    assert [row["id"] for row in filter_metadata_by_slice(rows, "202606")] == ["a", "c"]


def test_merge_metadata_for_slice_appends_new_month() -> None:
    existing = [
        {"id": "june", "upload_date": "20260601", "title": "June"},
        {"id": "may", "upload_date": "20260501", "title": "May"},
    ]
    new_rows = [{"id": "april", "upload_date": "20260415", "title": "April"}]

    merged = merge_metadata_for_slice(existing, new_rows, "202604", refresh=False)

    assert [row["id"] for row in merged] == ["june", "may", "april"]


def test_merge_metadata_for_slice_refresh_replaces_month_only() -> None:
    existing = [
        {"id": "old-june", "upload_date": "20260601", "title": "Old"},
        {"id": "may", "upload_date": "20260501", "title": "May"},
    ]
    new_rows = [
        {"id": "new-june-a", "upload_date": "20260610", "title": "A"},
        {"id": "new-june-b", "upload_date": "20260620", "title": "B"},
    ]

    merged = merge_metadata_for_slice(existing, new_rows, "202606", refresh=True)

    assert [row["id"] for row in merged] == ["may", "new-june-a", "new-june-b"]


def test_should_stop_channel_scan_when_older_than_slice() -> None:
    assert should_stop_channel_scan("20260531", "202606")
    assert not should_stop_channel_scan("20260601", "202606")


def test_confirm_slice_refresh_defaults_to_no() -> None:
    assert not confirm_slice_refresh("metadata row(s)", "2026-06", 3, input_fn=lambda _: "")


def test_confirm_slice_refresh_accepts_yes() -> None:
    assert confirm_slice_refresh(
        "summary row(s)",
        "2026-06",
        1,
        input_fn=lambda _: "y",
    )


def test_available_slice_labels_from_upload_dates() -> None:
    rows = [
        {"id": "a", "upload_date": "20260601"},
        {"id": "b", "upload_date": "20260515"},
        {"id": "c", "upload_date": ""},
    ]
    assert available_slice_labels(rows) == ["2026-06", "2026-05"]


def test_exit_missing_slice_metadata_prints_help(capsys) -> None:
    from pathlib import Path

    with pytest.raises(SystemExit) as exc:
        exit_missing_slice_metadata(
            "2026-05",
            csv_path=Path("data/videos.csv"),
            all_metadata=[{"id": "a", "upload_date": "20260601"}],
        )

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "No metadata for study slice 2026-05" in output
    assert "python scrape_metadata.py --slice 2026-05" in output
    assert "Months already in videos.csv: 2026-06" in output
