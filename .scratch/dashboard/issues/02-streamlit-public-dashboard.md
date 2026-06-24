# Issue 02: Streamlit public dashboard (table + trends)

Status: done

PRD: `.scratch/dashboard/PRD.md`

## Goal

Build the public-facing Streamlit app: header, freshness date, headline metrics, 2–3 trend charts, and a filterable video table with YouTube links.

## Background

Reads **only** from `publish/videos_with_summaries.csv` and `publish/last_updated.json`. No dependency on gitignored `data/`. Uses `scraper/summary_status.py` from issue 01.

## Tasks

1. **Dependencies**
   - Add `streamlit` and `pandas` to `requirements.txt` with pinned or minimum versions consistent with repo style.

2. **Create `dashboard/app.py`**
   - Load publish CSV + JSON at startup (cache with `@st.cache_data` if appropriate).
   - Derive `summary_status` column via `summary_status()`.
   - Derive `upload_month` from `upload_date` for charts/filters.

3. **Header section**
   - Title and one-line description (Patrick Boyle video catalog).
   - Credit Patrick Boyle; link to his YouTube channel (use channel URL from data or a constant in config).
   - Link to this repo on GitHub (use a placeholder constant like `GITHUB_REPO_URL` in `dashboard/config.py` or `scraper/config.py` — operator fills in real URL).

4. **Freshness**
   - Prominent “Data as of {published_at}” from `last_updated.json` (format human-readably).

5. **Headline metrics** (`st.columns` + `st.metric`)
   - Total videos
   - Summaries complete / pending / missing (from JSON or recompute)
   - Total views (sum `view_count` as int)

6. **Trends** (at least 2)
   - Uploads per month (bar or line chart)
   - Summary coverage by month (stacked or grouped: complete / pending / missing) **or** simple coverage % over months
   - Optional third: average views by upload month

7. **Video table**
   - Filters: upload month (selectbox), summary status (multiselect or selectbox)
   - Columns: title, upload date (formatted), views, duration (formatted mm:ss or human), status, summary preview, YouTube link
   - `complete`: show truncated summary (~120 chars); full text in `st.expander` or detail selectbox (pick simplest)
   - `pending` / `missing`: show status label, not raw URL or empty cell
   - YouTube link uses `webpage_url`; open in new tab via markdown link or `st.column_config.LinkColumn`

8. **Disclaimer footer**
   - AI-generated summaries of public videos; not affiliated with Patrick Boyle.

9. **Smoke test**
   - App runs with `streamlit run dashboard/app.py` when `publish/` contains sample data (issue 01 output or test fixture copied to `publish/` for dev).

## Acceptance criteria

- [ ] `streamlit run dashboard/app.py` loads without error when `publish/` artifacts exist.
- [ ] All videos appear in the table; filters work.
- [ ] URL-placeholder rows display as **pending**, not as summary text.
- [ ] At least two trend charts render.
- [ ] “Data as of” visible on load.
- [ ] No reads from `data/videos.csv` or `data/summaries.csv`.

## Out of scope

- Operator panel (issue 03)
- Streamlit Cloud deploy / README (issue 04)
- `st.session_state` persistence beyond filter defaults (keep simple)

## Depends on

- Issue 01 (`publish/` artifacts + `summary_status.py`)
