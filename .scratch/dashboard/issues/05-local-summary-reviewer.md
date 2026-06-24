# Issue 05: Local summary reviewer

Status: done

PRD: `.scratch/dashboard/PRD.md`

## Goal

Add a **local-only** Streamlit app so the operator can fix URL-placeholder summaries (`pending` status) by pasting replacement text — without editing `summaries.csv` by hand.

## Background

When Brave Copy fails, `extract_summaries.py` writes the YouTube URL into `summary` instead of summary text. The cloud **Operator** page lists these after publish, but fixing them still means hunting rows in a CSV.

`scraper/csv_io.write_summaries` already supports per-id updates. This issue wraps that in a small inbox UI.

**Explicit non-goal:** SQLite or any new database. CSV remains the source of truth.

## Tasks

1. **Entry point**
   - Add `review_app.py` at repo root (mirrors `app.py` for the public dashboard).
   - `streamlit run review_app.py` from repo root.
   - Module implementation in `dashboard/review.py` (keep scraper scripts separate from UI).

2. **Load local data**
   - Read `data/videos.csv` + `data/summaries.csv` via `merge_videos_and_summaries`.
   - Fail clearly if `data/videos.csv` is missing (same message style as scraper).
   - Derive `status` per row with `summary_status` from `scraper/summary_status.py`.
   - Derive `upload_month` with `parse_upload_month` for optional filtering.

3. **Queue logic** (pure functions, testable)
   - `pending_queue(videos: list[dict], *, slice_month: str | None = None) -> list[dict]`
     - Filter to `status == "pending"`.
     - If `slice_month` set (e.g. `"2026-06"`), keep rows where `upload_month == slice_month`.
     - Preserve stable order (video order from `videos.csv`).
   - `queue_counts(videos: list[dict]) -> dict[str, int]` — complete / pending / missing totals.

4. **UI — header**
   - Title: “Summary Reviewer (local)”.
   - Caption: reads/writes gitignored `data/summaries.csv`; run before `publish_data.py`.
   - Metrics row: pending, missing, complete counts.
   - Optional slice filter: `st.selectbox` of distinct `upload_month` values plus “All months”.

5. **UI — inbox card** (one video at a time)
   - Track current index in `st.session_state` (reset when queue changes).
   - Show: status badge, position in queue (`3 of 4`), title, formatted upload date, views, duration.
   - `st.link_button` or markdown link to `webpage_url` (“Open in YouTube”).
   - Read-only `st.text_area` or `st.code` for current bad summary (the URL).
   - Editable `st.text_area` for replacement (keyed by video id so state resets per row).
   - **Save & next**: validate non-empty and not URL-like (`summary_status(new_text) != "pending"`); call `write_summaries({id: new_text})`; optionally `clear_failed_id(id)`; `st.success`; advance index; `st.rerun`.
   - **Skip**: advance without writing.
   - **Prev / Next**: navigate within queue without saving.

6. **Empty queue**
   - `st.success("No pending summaries.")`
   - Reminder: `python publish_data.py`, then commit `publish/` and push.

7. **Update operator docs** (minimal)
   - `dashboard/operator.py` — step 3 in `REFRESH_STEPS`: `streamlit run review_app.py` instead of manual CSV edit.
   - `README.md` — same step in publish workflow section (one line change).

8. **Tests** (`tests/test_review.py`)
   - `pending_queue` returns only pending rows; slice filter works.
   - `pending_queue` empty when no URL placeholders.
   - Save path: mock or `tmp_path` — `write_summaries` called with correct id/text (integration-style test against temp CSVs is fine).
   - Validation: reject empty save; reject text that still looks like a URL.

## Acceptance criteria

- [ ] `streamlit run review_app.py` loads local `data/` and shows pending count matching URL-placeholder rows.
- [ ] Queue shows title, metadata, YouTube link, and current bad value for each pending video.
- [ ] **Save & next** writes replacement to `data/summaries.csv` via `write_summaries`; row no longer appears as pending on reload.
- [ ] **Skip** and **Prev / Next** work without corrupting CSV.
- [ ] Slice filter limits queue to one `YYYY-MM` month when selected.
- [ ] Empty queue shows publish reminder.
- [ ] `pytest` passes for new tests.
- [ ] No writes to `publish/` from the reviewer app.
- [ ] Public `app.py` / cloud Operator page unchanged except refresh-step text.

## Out of scope

- SQLite or new data files
- Deploying reviewer to Streamlit Cloud
- Running Brave extract from the UI
- Browse/audit of `complete` summaries (“approve” workflow)
- Editing `missing` rows (no summary row yet — still `extract_summaries.py`)

## Depends on

- Issues 01–03 (summary_status, csv_io, dashboard patterns)

## References

- URL-placeholder examples: `data/summaries.csv` rows `cvOuN5KqufE`, `e-tapKoT1K0`, `n_wNCLdlV7w`
- Write API: `scraper/csv_io.write_summaries`
- Status helper: `scraper/summary_status.summary_status`
