# Issue 03: Operator panel (read-only checklist)

Status: done

PRD: `.scratch/dashboard/PRD.md`

## Goal

Add a read-only **Operator** view to the Streamlit app: pending-summary checklist, missing count, and weekly refresh instructions.

## Background

You refresh data locally each week; the cloud app cannot run Brave extract. This page is your post-publish verification checklist and documents the ritual for future you.

## Tasks

1. **Multipage Streamlit layout**
   - Use `st.navigation` or `pages/` pattern (Streamlit ≥1.36) — pick what matches installed Streamlit version.
   - Pages: **Catalog** (existing `app.py` content from issue 02) and **Operator**.

2. **Operator page content**
   - **Pending summaries table**: all rows where `summary_status == "pending"` — columns: `id`, `title`, `webpage_url` (clickable).
   - **Missing count**: number of `missing` rows; short note that these need local `extract_summaries.py` run.
   - **Failed extracts**: static text pointing to local `data/failed_ids.txt` and `python extract_summaries.py --retry-failed` (not read from cloud — file is gitignored).
   - **How to refresh** (numbered steps, mirror PRD):
     1. `python scrape_metadata.py` (optional `--slice`)
     2. `python extract_summaries.py --skip-existing`
     3. Fix URL-placeholder rows in local `summaries.csv`
     4. `python publish_data.py` (or whatever issue 01 named it)
     5. `git add publish/ && git commit && git push`
     6. Streamlit Cloud redeploys on push

3. **Metrics at top of Operator page**
   - Repeat pending / missing counts from `last_updated.json` for quick scan.

## Acceptance criteria

- [ ] Operator page accessible from app navigation.
- [ ] Pending table lists only URL-placeholder videos with working YouTube links.
- [ ] Refresh instructions are accurate for this repo’s scripts.
- [ ] No write-back to CSV or JSON from the UI.
- [ ] No password gate (v1).

## Out of scope

- Editing summaries in the browser
- Triggering scrape/extract from the UI
- Reading `data/failed_ids.txt` on Streamlit Cloud

## Depends on

- Issue 02 (`dashboard/app.py` structure)
