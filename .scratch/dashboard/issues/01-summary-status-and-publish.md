# Issue 01: Summary status helper and publish pipeline

Status: done

PRD: `.scratch/dashboard/PRD.md`

## Goal

Add shared summary-status logic and a publish step that writes dashboard-ready artifacts to `publish/`, separate from gitignored `data/`.

## Background

When Brave Copy fails, `summaries.csv` may contain a YouTube URL instead of summary text. The dashboard must classify each row as `complete`, `pending`, or `missing`. Published data lives in `publish/` and is committed to git; `data/` stays local.

## Tasks

1. **Add `scraper/summary_status.py`**
   - `summary_status(summary: str) -> str` returning `"complete"`, `"pending"`, or `"missing"`.
   - Rules (from PRD):
     - `missing`: empty or whitespace-only `summary`
     - `pending`: `summary.strip().lower().startswith("http")`
     - `complete`: otherwise
   - Optional helper: `parse_upload_month(upload_date: str) -> str` → `"YYYY-MM"` from `YYYYMMDD`, or `""` if invalid.

2. **Add publish paths to `scraper/config.py`**
   - `PUBLISH_DIR = PROJECT_ROOT / "publish"`
   - `PUBLISH_VIDEOS_CSV = PUBLISH_DIR / "videos_with_summaries.csv"`
   - `PUBLISH_LAST_UPDATED_JSON = PUBLISH_DIR / "last_updated.json"`

3. **Add publish module or extend export**
   - Prefer `publish_data.py` at repo root (mirrors `export_combined.py`) **or** extend `export_combined.py` with `--publish` flag — pick the clearest UX.
   - Reads from default `data/videos.csv` + `data/summaries.csv` (same as export today).
   - Writes `publish/videos_with_summaries.csv` (same columns as `COMBINED_FIELDS`).
   - Writes `publish/last_updated.json`:
     ```json
     {
       "published_at": "<ISO-8601 UTC>",
       "video_count": <int>,
       "summary_complete": <int>,
       "summary_pending": <int>,
       "summary_missing": <int>
     }
     ```
   - Print a reminder: commit `publish/` and push to refresh Streamlit Cloud.
   - Create `publish/` if missing.

4. **Update `.gitignore`**
   - Keep `data/*` artifacts ignored.
   - Ensure `publish/` is **not** ignored.
   - Add `publish/.gitkeep` only if needed for empty dir; prefer committing real data after first publish run.

5. **Tests** (`tests/test_summary_status.py`, extend `tests/test_csv_io.py` or new `tests/test_publish.py`)
   - URL placeholder → `pending`
   - Real summary text → `complete`
   - Empty → `missing`
   - Publish writes both files with correct counts (use `tmp_path` fixtures).

## Acceptance criteria

- [ ] `python publish_data.py` (or equivalent) creates `publish/videos_with_summaries.csv` and `publish/last_updated.json` from local `data/`.
- [ ] Status counts in JSON match row classifications.
- [ ] `pytest` passes for new tests.
- [ ] `publish/` is trackable by git (not gitignored).

## Out of scope

- Streamlit app
- README changes (issue 04)
- Committing real `publish/` data with secrets (no `click_positions.json`)

## Depends on

Nothing — implement first.
