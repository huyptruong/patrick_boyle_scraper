"""Load and prepare published dashboard data."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dashboard.formatting import (
    format_duration,
    format_upload_date,
    summary_preview_text,
)
from scraper.config import PUBLISH_LAST_UPDATED_JSON, PUBLISH_VIDEOS_CSV
from scraper.summary_status import parse_upload_month, summary_status


def load_publish_metadata(
    json_path: Path = PUBLISH_LAST_UPDATED_JSON,
) -> dict[str, object]:
    """Load publish/last_updated.json."""
    if not json_path.exists():
        raise FileNotFoundError(
            f"{json_path} not found. Run publish_data.py first."
        )
    with json_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_videos_dataframe(
    csv_path: Path = PUBLISH_VIDEOS_CSV,
) -> pd.DataFrame:
    """Load publish/videos_with_summaries.csv."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Run publish_data.py first."
        )
    return pd.read_csv(csv_path, dtype=str).fillna("")


def prepare_videos_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns used by charts and the video table."""
    prepared = df.copy()
    prepared["status"] = prepared["summary"].map(summary_status)
    prepared["upload_month"] = prepared["upload_date"].map(parse_upload_month)
    prepared["upload_date_display"] = prepared["upload_date"].map(format_upload_date)
    prepared["duration_display"] = prepared["duration"].map(format_duration)
    prepared["views"] = pd.to_numeric(prepared["view_count"], errors="coerce").fillna(0).astype(int)
    prepared["summary_preview"] = prepared.apply(
        lambda row: summary_preview_text(row["summary"], row["status"]),
        axis=1,
    )
    return prepared


def uploads_per_month(df: pd.DataFrame) -> pd.DataFrame:
    """Count videos uploaded each month."""
    counts = (
        df[df["upload_month"] != ""]
        .groupby("upload_month", as_index=False)
        .size()
        .rename(columns={"size": "uploads"})
        .sort_values("upload_month")
    )
    return counts.set_index("upload_month")


def summary_coverage_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Count complete / pending / missing summaries per upload month."""
    monthly = df[df["upload_month"] != ""]
    if monthly.empty:
        return pd.DataFrame(columns=["complete", "pending", "missing"])

    coverage = (
        monthly.groupby(["upload_month", "status"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    for column in ("complete", "pending", "missing"):
        if column not in coverage.columns:
            coverage[column] = 0
    return coverage[["complete", "pending", "missing"]]


def average_views_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Average view count per upload month."""
    averages = (
        df[df["upload_month"] != ""]
        .groupby("upload_month", as_index=False)["views"]
        .mean()
        .sort_values("upload_month")
    )
    averages["views"] = averages["views"].round(0).astype(int)
    return averages.set_index("upload_month")
