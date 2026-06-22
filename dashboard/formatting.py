"""Format publish data for dashboard display."""

from __future__ import annotations

from datetime import datetime

from dashboard.config import STATUS_LABELS, SUMMARY_PREVIEW_LENGTH
from scraper.summary_status import SummaryStatus, summary_status


def format_upload_date(upload_date: str) -> str:
    """Format YYYYMMDD as YYYY-MM-DD."""
    digits = upload_date.strip()
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return upload_date


def format_duration(duration: str) -> str:
    """Format duration seconds as mm:ss or h:mm:ss."""
    try:
        total_seconds = int(float(duration))
    except (ValueError, TypeError):
        return ""

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_published_at(published_at: str) -> str:
    """Format ISO-8601 publish timestamp for display."""
    normalized = published_at.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return published_at
    return timestamp.strftime("%B %d, %Y at %H:%M UTC")


def summary_preview_text(summary: str, status: SummaryStatus) -> str:
    """Table preview: truncated summary or status label."""
    if status != "complete":
        return STATUS_LABELS[status]
    text = summary.strip()
    if len(text) <= SUMMARY_PREVIEW_LENGTH:
        return text
    return text[: SUMMARY_PREVIEW_LENGTH - 1].rstrip() + "…"


def status_label(summary: str) -> str:
    """Human-readable status label for a summary field."""
    return STATUS_LABELS[summary_status(summary)]
