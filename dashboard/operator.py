"""Operator checklist page for weekly data refresh."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.formatting import format_published_at

REFRESH_STEPS = (
    "Run `python scrape_metadata.py` (optional `--slice YYYY-MM`).",
    "Run `python extract_summaries.py --skip-existing`.",
    "Run `streamlit run review_app.py` to fix URL-placeholder summaries.",
    "Run `python publish_data.py`.",
    "Run `git add publish/ && git commit && git push`.",
    "Streamlit Cloud redeploys automatically on push.",
)


def pending_videos(videos: pd.DataFrame) -> pd.DataFrame:
    """Rows where summary is a URL placeholder."""
    return videos[videos["status"] == "pending"].copy()


def render_operator_page(metadata: dict[str, object], videos: pd.DataFrame) -> None:
    """Read-only operator checklist for local refresh workflow."""
    st.title("Operator")
    st.markdown(
        "Post-publish checklist. Extraction runs on your machine — this page reads "
        "the last published snapshot only."
    )

    published_at = str(metadata.get("published_at", ""))
    st.info(f"**Published snapshot:** {format_published_at(published_at)}")

    pending_count = int(metadata.get("summary_pending", 0))
    missing_count = int(metadata.get("summary_missing", 0))
    metric_columns = st.columns(2)
    metric_columns[0].metric("Summaries pending manual fix", pending_count)
    metric_columns[1].metric("Summaries missing", missing_count)

    st.subheader("Pending manual extract")
    st.caption(
        "These videos have a YouTube URL in `summaries.csv` instead of summary text. "
        "Re-run extract or paste the summary locally, then publish again."
    )
    pending = pending_videos(videos)
    if pending.empty:
        st.success("No pending summaries in the published snapshot.")
    else:
        display = pending[["id", "title", "webpage_url"]].rename(
            columns={
                "id": "Video ID",
                "title": "Title",
                "webpage_url": "YouTube",
            }
        )
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "YouTube": st.column_config.LinkColumn(
                    display_text="Watch",
                    validate=r"^https?://",
                ),
            },
        )

    st.subheader("Missing summaries")
    if missing_count == 0:
        st.success("Every published video has a summary row (complete or pending).")
    else:
        st.warning(
            f"**{missing_count}** videos have no summary in the published snapshot. "
            "Run `python extract_summaries.py --skip-existing` locally, then "
            "`python publish_data.py` and push."
        )

    st.subheader("Failed extracts (local only)")
    st.markdown(
        "After a local extract run, check `data/failed_ids.txt` for videos that "
        "could not be automated. Retry with:\n\n"
        "```bash\npython extract_summaries.py --retry-failed\n```\n\n"
        "This file is not available on Streamlit Cloud."
    )

    st.subheader("How to refresh the dashboard")
    for index, step in enumerate(REFRESH_STEPS, start=1):
        st.markdown(f"{index}. {step}")
