"""Patrick Boyle video catalog dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit runs this file with dashboard/ on sys.path, not the repo root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from dashboard.config import (
    GITHUB_REPO_URL,
    PATRICK_BOYLE_CHANNEL_NAME,
    PATRICK_BOYLE_CHANNEL_URL,
    STATUS_LABELS,
)
from dashboard.formatting import format_published_at
from dashboard.load_data import (
    average_views_by_month,
    load_publish_metadata,
    load_videos_dataframe,
    prepare_videos_dataframe,
    summary_coverage_by_month,
    uploads_per_month,
)
from dashboard.operator import render_operator_page
from scraper.config import PUBLISH_LAST_UPDATED_JSON, PUBLISH_VIDEOS_CSV


@st.cache_data
def load_dashboard_data() -> tuple[dict[str, object], "pd.DataFrame"]:
    import pandas as pd

    metadata = load_publish_metadata(PUBLISH_LAST_UPDATED_JSON)
    videos = prepare_videos_dataframe(load_videos_dataframe(PUBLISH_VIDEOS_CSV))
    return metadata, videos


def render_catalog_page(metadata: dict[str, object], videos: "pd.DataFrame") -> None:
    st.title("Patrick Boyle Video Catalog")
    st.markdown(
        "Explore Patrick Boyle's YouTube videos with metadata and AI-generated summaries."
    )
    st.markdown(
        f"Channel: [{PATRICK_BOYLE_CHANNEL_NAME}]({PATRICK_BOYLE_CHANNEL_URL}) · "
        f"[GitHub]({GITHUB_REPO_URL})"
    )

    published_at = str(metadata.get("published_at", ""))
    st.info(f"**Data as of** {format_published_at(published_at)}")

    total_views = int(videos["views"].sum())
    columns = st.columns(5)
    columns[0].metric("Total videos", int(metadata.get("video_count", len(videos))))
    columns[1].metric("Summaries complete", int(metadata.get("summary_complete", 0)))
    columns[2].metric("Summaries pending", int(metadata.get("summary_pending", 0)))
    columns[3].metric("Summaries missing", int(metadata.get("summary_missing", 0)))
    columns[4].metric("Total views", f"{total_views:,}")

    st.subheader("Trends")
    chart_columns = st.columns(3)

    uploads = uploads_per_month(videos)
    coverage = summary_coverage_by_month(videos)
    averages = average_views_by_month(videos)

    chart_columns[0].markdown("**Uploads per month**")
    if uploads.empty:
        chart_columns[0].caption("No upload dates available.")
    else:
        chart_columns[0].bar_chart(uploads)

    chart_columns[1].markdown("**Summary coverage by month**")
    if coverage.empty:
        chart_columns[1].caption("No upload dates available.")
    else:
        chart_columns[1].bar_chart(coverage)

    chart_columns[2].markdown("**Average views by upload month**")
    if averages.empty:
        chart_columns[2].caption("No upload dates available.")
    else:
        chart_columns[2].line_chart(averages)

    st.subheader("Videos")

    months = sorted(month for month in videos["upload_month"].unique() if month)
    month_options = ["All months"] + months
    status_options = list(STATUS_LABELS.keys())

    filter_columns = st.columns(2)
    selected_month = filter_columns[0].selectbox("Upload month", month_options)
    selected_statuses = filter_columns[1].multiselect(
        "Summary status",
        options=status_options,
        default=status_options,
        format_func=lambda value: STATUS_LABELS[value],
    )

    filtered = videos[videos["status"].isin(selected_statuses)]
    if selected_month != "All months":
        filtered = filtered[filtered["upload_month"] == selected_month]

    st.caption(f"Showing {len(filtered)} of {len(videos)} videos")

    display = filtered[
        [
            "title",
            "upload_date_display",
            "views",
            "duration_display",
            "status",
            "summary_preview",
            "webpage_url",
        ]
    ].rename(
        columns={
            "title": "Title",
            "upload_date_display": "Upload date",
            "views": "Views",
            "duration_display": "Duration",
            "status": "Status",
            "summary_preview": "Summary",
            "webpage_url": "YouTube",
        }
    )
    display["Status"] = display["Status"].map(STATUS_LABELS)

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Views": st.column_config.NumberColumn(format="%d"),
            "YouTube": st.column_config.LinkColumn(
                display_text="Watch",
                validate=r"^https?://",
            ),
        },
    )

    complete_videos = filtered[filtered["status"] == "complete"]
    if not complete_videos.empty:
        with st.expander("Read full summary"):
            titles = complete_videos["title"].tolist()
            selected_title = st.selectbox("Video", titles, label_visibility="collapsed")
            summary_row = complete_videos.loc[
                complete_videos["title"] == selected_title
            ].iloc[0]
            st.markdown(summary_row["summary"])

    st.divider()
    st.caption(
        "Summaries are AI-generated from public YouTube videos. "
        "This site is not affiliated with Patrick Boyle."
    )


def main() -> None:
    st.set_page_config(
        page_title="Patrick Boyle Video Catalog",
        page_icon="📊",
        layout="wide",
    )
    metadata, videos = load_dashboard_data()

    def catalog() -> None:
        render_catalog_page(metadata, videos)

    def operator() -> None:
        render_operator_page(metadata, videos)

    page = st.navigation(
        [
            st.Page(catalog, title="Catalog", icon="📊", default=True),
            st.Page(operator, title="Operator", icon="🛠️"),
        ]
    )
    page.run()


if __name__ == "__main__":
    main()
