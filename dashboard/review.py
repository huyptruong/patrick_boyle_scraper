"""Local summary reviewer — fix URL-placeholder rows before publish."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from dashboard.formatting import format_duration, format_upload_date, status_label
from scraper.config import FAILED_IDS_PATH, SUMMARIES_CSV, VIDEOS_CSV
from scraper.csv_io import clear_failed_id, merge_videos_and_summaries, write_summaries
from scraper.summary_status import parse_upload_month, summary_status

PUBLISH_REMINDER = (
    "Run `python publish_data.py`, then commit `publish/` and push to refresh the dashboard."
)


def prepare_video_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Add status and upload_month to merged video rows."""
    prepared: list[dict[str, str]] = []
    for row in rows:
        summary = row.get("summary", "")
        enriched = dict(row)
        enriched["status"] = summary_status(summary)
        enriched["upload_month"] = parse_upload_month(row.get("upload_date", ""))
        prepared.append(enriched)
    return prepared


def load_local_videos(
    videos_path: Path = VIDEOS_CSV,
    summaries_path: Path = SUMMARIES_CSV,
) -> list[dict[str, str]]:
    """Load and enrich local data/videos.csv + data/summaries.csv."""
    rows = merge_videos_and_summaries(videos_path, summaries_path)
    return prepare_video_rows(rows)


def pending_queue(
    videos: list[dict[str, str]],
    *,
    slice_month: str | None = None,
) -> list[dict[str, str]]:
    """Pending rows in video order, optionally filtered by upload month."""
    queue = [row for row in videos if row.get("status") == "pending"]
    if slice_month:
        queue = [row for row in queue if row.get("upload_month") == slice_month]
    return queue


def queue_counts(videos: list[dict[str, str]]) -> dict[str, int]:
    """Count complete / pending / missing summaries."""
    counts = {"complete": 0, "pending": 0, "missing": 0}
    for row in videos:
        status = row.get("status", summary_status(row.get("summary", "")))
        counts[status] = counts.get(status, 0) + 1
    return counts


def validate_replacement_summary(text: str) -> str | None:
    """Return an error message if text is not a valid replacement, else None."""
    stripped = text.strip()
    if not stripped:
        return "Summary cannot be empty."
    if summary_status(stripped) == "pending":
        return "Summary still looks like a URL. Paste the full summary text."
    return None


def save_replacement_summary(
    video_id: str,
    summary: str,
    *,
    summaries_path: Path = SUMMARIES_CSV,
    failed_ids_path: Path = FAILED_IDS_PATH,
) -> None:
    """Write replacement summary and clear failed-id log entry if present."""
    write_summaries({video_id: summary.strip()}, summaries_path)
    clear_failed_id(video_id, failed_ids_path)


def _slice_options(videos: list[dict[str, str]]) -> list[str]:
    months = sorted({row["upload_month"] for row in videos if row.get("upload_month")})
    return ["All months", *months]


def _queue_signature(queue: list[dict[str, str]]) -> tuple[str, ...]:
    return tuple(row["id"] for row in queue)


def _sync_queue_index(queue: list[dict[str, str]]) -> int:
    """Keep session index valid when the queue changes."""
    signature = _queue_signature(queue)
    if st.session_state.get("review_queue_signature") != signature:
        st.session_state.review_queue_signature = signature
        st.session_state.review_index = 0

    index = int(st.session_state.get("review_index", 0))
    if not queue:
        st.session_state.review_index = 0
        return 0

    clamped = max(0, min(index, len(queue) - 1))
    st.session_state.review_index = clamped
    return clamped


def _set_queue_index(index: int) -> None:
    st.session_state.review_index = index


def _render_empty_queue() -> None:
    st.success("No pending summaries.")
    st.info(PUBLISH_REMINDER)


def _render_inbox_card(queue: list[dict[str, str]], index: int) -> None:
    row = queue[index]
    video_id = row["id"]
    position = index + 1
    total = len(queue)

    st.markdown(f"**{status_label(row.get('summary', ''))}** · {position} of {total}")
    st.subheader(row.get("title") or video_id)

    metadata_parts: list[str] = []
    upload_display = format_upload_date(row.get("upload_date", ""))
    if upload_display:
        metadata_parts.append(f"Uploaded {upload_display}")
    view_count = row.get("view_count", "").strip()
    if view_count.isdigit():
        metadata_parts.append(f"{int(view_count):,} views")
    duration_display = format_duration(row.get("duration", ""))
    if duration_display:
        metadata_parts.append(duration_display)
    if metadata_parts:
        st.caption(" · ".join(metadata_parts))

    webpage_url = row.get("webpage_url", "")
    if webpage_url:
        st.link_button("Open in YouTube", webpage_url)

    st.markdown("**Current value (bad)**")
    st.code(row.get("summary", ""), language=None)

    replacement = st.text_area(
        "Paste replacement summary",
        height=240,
        key=f"replacement_{video_id}",
        placeholder="Paste the summary from Brave Ask…",
    )

    action_columns = st.columns([2, 1, 1, 1])
    if action_columns[0].button("Save & next", type="primary", use_container_width=True):
        error = validate_replacement_summary(replacement)
        if error:
            st.error(error)
        else:
            save_replacement_summary(video_id, replacement)
            st.success(f"Saved {video_id}.")
            _set_queue_index(index)
            st.rerun()

    if action_columns[1].button("Skip", use_container_width=True):
        _set_queue_index(min(index + 1, len(queue) - 1))
        st.rerun()

    nav_columns = st.columns(2)
    if nav_columns[0].button("← Prev", disabled=index == 0, use_container_width=True):
        _set_queue_index(index - 1)
        st.rerun()
    if nav_columns[1].button(
        "Next →",
        disabled=index >= len(queue) - 1,
        use_container_width=True,
    ):
        _set_queue_index(index + 1)
        st.rerun()


def render_review_page(
    videos_path: Path = VIDEOS_CSV,
    summaries_path: Path = SUMMARIES_CSV,
) -> None:
    """Render the local summary reviewer UI."""
    videos = load_local_videos(videos_path, summaries_path)
    counts = queue_counts(videos)

    st.title("Summary Reviewer (local)")
    st.caption(
        "Reads and writes gitignored `data/summaries.csv`. "
        "Run after `extract_summaries.py` and before `publish_data.py`."
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric("Pending", counts["pending"])
    metric_columns[1].metric("Missing", counts["missing"])
    metric_columns[2].metric("Complete", counts["complete"])

    slice_options = _slice_options(videos)
    selected_slice = st.selectbox("Upload month", slice_options)
    slice_month = None if selected_slice == "All months" else selected_slice

    queue = pending_queue(videos, slice_month=slice_month)
    if not queue:
        _render_empty_queue()
        return

    index = _sync_queue_index(queue)
    _render_inbox_card(queue, index)


def main() -> None:
    st.set_page_config(
        page_title="Summary Reviewer",
        page_icon="✏️",
        layout="wide",
    )
    try:
        render_review_page()
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()


if __name__ == "__main__":
    main()
