# PRD: Patrick Boyle public dashboard (v1)

## Status

v1 issues done. **Next:** issue 05 — local summary reviewer (`ready-for-agent`).

## Issues

| # | File | Summary |
|---|------|---------|
| 01 | `.scratch/dashboard/issues/01-summary-status-and-publish.md` | Summary status helper + `publish/` pipeline |
| 02 | `.scratch/dashboard/issues/02-streamlit-public-dashboard.md` | Public Streamlit catalog, trends, table |
| 03 | `.scratch/dashboard/issues/03-operator-panel.md` | Read-only operator checklist page |
| 04 | `.scratch/dashboard/issues/04-readme-and-deploy.md` | README, CONTEXT, first publish, deploy docs |
| 05 | `.scratch/dashboard/issues/05-local-summary-reviewer.md` | Local Streamlit inbox to fix URL-placeholder summaries |

## Summary

Ship a **public Streamlit dashboard** that lets visitors explore Patrick Boyle’s YouTube catalog: metadata plus AI-generated summaries, simple trends, and clickable YouTube links. The dashboard is a **portfolio piece** (LinkedIn, hiring managers) in the spirit of [layoffs.fyi](https://layoffs.fyi): a clear table with data people can scan.

Data is **refreshed manually** on the operator’s machine (scrape + Brave extract), then **published** to GitHub so Streamlit Cloud serves the latest snapshot. The dashboard shows **“Data as of …”** so visitors know how fresh it is.

## Goals

1. **Public catalog** — browsable table of videos with title, date, views, duration, summary (or pending state), and YouTube link.
2. **Trends** — a few headline charts/metrics from existing metadata (no new data sources).
3. **Summary status** — distinguish complete summaries, pending manual extract (URL placeholder), and missing summaries.
4. **Portfolio-ready** — live URL, public repo, README story; attribution to Patrick Boyle and data sources.
5. **Operator visibility** — cloud Operator page (read-only checklist) plus **local Summary Reviewer** (issue 05) to paste-fix URL-placeholder rows before publish.

## Non-goals (v1)

- Running Brave UI extraction from the cloud dashboard.
- Next.js, custom front-end, or database (SQLite deferred; CSV + `write_summaries` is sufficient at current scale).
- User accounts, auth, or paywalls.
- Topic modeling / NLP search (later).
- Historical view-count time series (requires periodic snapshots; later).
- Hiding data or code — public repo + published snapshot is intentional.

## Users

| User | Needs |
|------|--------|
| **Public visitor** | Scan videos, spot patterns, read summaries, click through to YouTube. |
| **Operator (you)** | Weekly: extract locally → fix pending summaries in local Reviewer → publish → verify cloud Operator page. |
| **Hiring manager / LinkedIn** | Live demo, readable code, clear pipeline story end-to-end. |

## Architecture

### Two environments

```
LOCAL (operator Mac)                    CLOUD (Streamlit)
────────────────────                    ─────────────────
scrape_metadata.py                      app reads publish/
extract_summaries.py          git push  videos_with_summaries.csv
review_app.py (issue 05)                last_updated.json
publish_data.py                         Catalog + Operator (read-only)
```

Brave extract **cannot** run on Streamlit Cloud. The **public** dashboard is read-only over committed `publish/` artifacts. The **local Reviewer** reads/writes gitignored `data/summaries.csv` via existing `write_summaries`.

### Weekly operator workflow

1. Run `scrape_metadata.py` (full or `--slice YYYY-MM`).
2. Run `extract_summaries.py` (`--skip-existing` or slice).
3. Run `streamlit run review_app.py` — work through pending queue; paste replacements from Brave Ask.
4. Run `python publish_data.py`.
5. Commit `publish/` artifacts + push to GitHub.
6. Streamlit Cloud redeploys automatically on push; verify cloud **Operator** page.

Calendar reminder (weekly) is sufficient; no in-app scheduler required for v1.

### Publish vs local data

| Path | Git | Purpose |
|------|-----|---------|
| `data/videos.csv`, `data/summaries.csv` | **ignored** | Working copies on operator machine |
| `data/click_positions.json`, `data/run.log`, `data/failed_ids.txt` | **ignored** | Machine-specific / noisy |
| `publish/videos_with_summaries.csv` | **committed** | Dashboard data source |
| `publish/last_updated.json` | **committed** | Explicit refresh timestamp |

Local `data/` stays private; only `publish/` is the public snapshot.

## Data model

### Source: joined video row

Columns from `videos.csv` plus `summary` from `summaries.csv` (existing `COMBINED_FIELDS` in `scraper/config.py`).

### Summary status (derived, not stored)

Compute at load time for each row:

| Status | Rule | Dashboard display |
|--------|------|-------------------|
| `complete` | `summary` non-empty and does **not** look like a URL | Show summary text (truncated in table; expandable elsewhere) |
| `pending` | `summary` starts with `http` (URL placeholder from failed Copy click) | Badge: “Summary pending”; link to YouTube for manual follow-up |
| `missing` | No row in summaries or empty `summary` | Badge: “No summary” |

Detection rule for pending: `summary.strip().lower().startswith("http")`.

Optional aggregate fields for trends: `summary_status`, parsed `upload_month` from `upload_date` (`YYYYMMDD`).

### `last_updated.json`

Written at publish time:

```json
{
  "published_at": "2026-06-22T14:30:00Z",
  "video_count": 238,
  "summary_complete": 45,
  "summary_pending": 2,
  "summary_missing": 191
}
```

## Dashboard UI (v1)

### Layout

1. **Header** — project title, short description, credit to Patrick Boyle, link to YouTube channel and GitHub repo.
2. **Freshness** — prominent “Data as of {published_at}” from `last_updated.json`.
3. **Headline metrics** — `st.metric` row, e.g.:
   - Total videos
   - Summaries complete / pending / missing
   - Total views (sum of `view_count`)
4. **Trends** (2–3 charts) — from metadata only:
   - Uploads per month (`upload_date` → month)
   - Summary coverage over time or by month (complete vs pending vs missing)
   - Optional: average views by upload month (snapshot cross-section)
5. **Video table** — sortable/filterable:
   - Columns: title, upload date, views, duration, summary status, YouTube link
   - Summary column: text preview for `complete`, status badge otherwise
   - Filter: month, summary status
   - YouTube links open in new tab (`webpage_url`)

### Operator panel (v1 — read-only)

Separate Streamlit page or section (no password required for v1; optional later):

- Table of `pending` rows (id, title, YouTube link)
- Count of `missing` and reference to `data/failed_ids.txt` workflow locally
- Short “How to refresh” instructions mirroring README weekly steps

No write-back to CSV from the cloud app.

### Local Summary Reviewer (issue 05)

Separate **local-only** Streamlit app (not deployed to Streamlit Cloud). Runs on operator machine between extract and publish.

**Queue:** videos where `summary_status == "pending"` (URL placeholder). Optional slice filter (`upload_month`).

**Per-video card:**

- Title, upload date, views, duration
- Link to YouTube (`webpage_url`)
- Read-only display of current bad value (the URL)
- Text area for pasted replacement summary
- **Save & next** — `write_summaries({id: text})`, advance queue
- **Skip** — leave unchanged, move on
- **Prev / Next** navigation within queue

**Empty queue:** success message + reminder to run `publish_data.py`.

**Data layer:** reuse `scraper/csv_io.read_summaries` / `write_summaries` and `merge_videos_and_summaries`. No SQLite, no new stored status fields.

## Tech stack

- **Python 3.12** (match existing repo)
- **Streamlit** — sole web framework
- **pandas** — load CSV, aggregates, charts via `st.bar_chart` / `st.line_chart`
- **Streamlit Cloud** — hosting, connected to GitHub repo

Add `streamlit` (and `pandas` if not already) to `requirements.txt`. Entry point: `dashboard/app.py` or repo-root `app.py` (decide in first implement issue).

## Repository changes (high level)

1. `publish/` directory with committed artifacts.
2. Extend or wrap `export_combined.py` to write `publish/videos_with_summaries.csv` + `publish/last_updated.json` with status counts.
3. Shared `summary_status(summary: str) -> str` helper (e.g. `scraper/summary_status.py`) used by export and dashboard.
4. Update `.gitignore`: keep `data/*` ignored; **do not** ignore `publish/`.
5. `dashboard/app.py` Streamlit app.
6. README section: dashboard, publish workflow, Streamlit Cloud deploy steps, portfolio attribution.

## Success criteria (v1 done)

- [ ] `streamlit run dashboard/app.py` works locally against `publish/` data.
- [ ] Public Streamlit Cloud URL loads without operator setup.
- [ ] Table shows all videos; YouTube links work.
- [ ] URL-placeholder rows show as **pending**, not as summary text.
- [ ] At least two trend visualizations render from real data.
- [ ] “Data as of” date visible on every page load.
- [ ] README documents weekly publish ritual in under 10 steps.
- [ ] No secrets or `click_positions.json` committed.

## Phases after v1

| Phase | Feature | Status |
|-------|---------|--------|
| 1.5 | Local Summary Reviewer (paste-fix pending rows) | Issue 05 — **next** |
| 2 | Browse all summaries locally; optional “approve” audit | Later |
| 2 | Trigger metadata scrape from UI | Later |
| 2 | Password-gated operator tab on cloud (read-only alerts only) | Later |
| 3 | SQLite (only if version history, search, or multi-operator needs emerge) | Deferred |
| 3 | Search, topic tags from summary text | Later |
| 3 | Prettier public site (only if Streamlit theme insufficient) | Later |
| 3 | Periodic metadata snapshots for true view-count trends | Later |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Forgot to commit `publish/` after extract | Publish script prints clear “commit these files” reminder; operator panel lists pending count |
| Large summary text breaks table layout | Truncate in table; expander or detail view for full text |
| Streamlit cold start on free tier | Acceptable for portfolio; mention in README |
| Summary content / attribution | Disclaimer: AI summaries of public videos; link to source; not affiliated with Patrick Boyle unless stated |

## Open decisions (resolve in implement, not blockers)

1. **App path** — `dashboard/app.py` vs root `app.py` (prefer `dashboard/` to separate from scraper scripts).
2. **Summary display** — expander per row vs separate “detail” selectbox (pick simplest in implement).
3. **Streamlit theme** — default vs minimal custom CSS for portfolio polish.

## References

- Existing pipeline: `scrape_metadata.py` → `extract_summaries.py` → `export_combined.py`
- ADR-0001: study-slice merge semantics (`docs/adr/0001-study-slice-csv-merge.md`)
- Domain glossary: `CONTEXT.md`
- URL-placeholder example: `data/summaries.csv` rows where `summary` is a YouTube URL

## Conversation decisions captured

- **Audience:** you first; public LinkedIn / portfolio for finance-adjacent traffic.
- **Vibe:** layoffs.fyi — table-first, trends as hook, iterate features over time.
- **Refresh:** manual weekly on local machine; git push updates cloud; show extract/publish date on dashboard.
- **Stack:** Python + Streamlit only; no Next.js for v1.
- **Data exposure:** public code + published snapshot is a feature; protect attribution, not secrecy.
- **Summary fixes:** local Reviewer UI, not raw CSV editing; still `write_summaries` under the hood — no database migration.
