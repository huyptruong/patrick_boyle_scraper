"""Classify summary text for dashboard display."""

from __future__ import annotations

from typing import Literal

SummaryStatus = Literal["complete", "pending", "missing"]


def summary_status(summary: str) -> SummaryStatus:
    """Return complete, pending (URL placeholder), or missing."""
    text = summary.strip()
    if not text:
        return "missing"
    if text.lower().startswith("http"):
        return "pending"
    return "complete"


def parse_upload_month(upload_date: str) -> str:
    """Parse YYYYMMDD upload_date to YYYY-MM, or empty string if invalid."""
    digits = upload_date.strip()
    if len(digits) < 6 or not digits[:6].isdigit():
        return ""
    return f"{digits[:4]}-{digits[4:6]}"
