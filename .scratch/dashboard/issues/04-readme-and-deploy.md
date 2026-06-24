# Issue 04: README, first publish, and Streamlit Cloud deploy

Status: done

PRD: `.scratch/dashboard/PRD.md`

## Goal

Document the dashboard and weekly publish workflow; run first publish with real data; add Streamlit Cloud deployment instructions.

## Background

Portfolio piece needs a live URL and README story. `publish/` must contain real (non-secret) data committed to the repo.

## Tasks

1. **README updates** (`README.md`)
   - New section: **Dashboard** — what it is, link placeholder for live Streamlit URL.
   - **Publish workflow** (≤10 steps): scrape → extract → fix pending → publish script → commit `publish/` → push.
   - Clarify `data/` vs `publish/` split (local working copies vs public snapshot).
   - **Streamlit Cloud deploy**:
     - Connect GitHub repo
     - Main file path: `dashboard/app.py`
     - Python version matches project (3.12)
     - Redeploys on push automatically
   - Attribution disclaimer for Patrick Boyle / AI summaries.

2. **Update `CONTEXT.md`**
   - Add glossary entries: **Publish**, **Summary status** (`complete` / `pending` / `missing`), **Dashboard**.

3. **First real publish**
   - Run publish script against current local `data/` (if present on operator machine).
   - Commit `publish/videos_with_summaries.csv` and `publish/last_updated.json`.
   - Verify no secrets in committed files.

4. **Optional: `dashboard/README.md`**
   - Only if README is getting long — short pointer to run locally: `streamlit run dashboard/app.py`.

## Acceptance criteria

- [ ] README documents full weekly ritual and `data/` vs `publish/` split.
- [ ] Streamlit Cloud setup steps are accurate for `dashboard/app.py`.
- [ ] `CONTEXT.md` updated with new terms.
- [ ] `publish/` contains committed real data (or explicit note in issue comment if operator machine has no data — then commit minimal fixture with README note to re-run publish).
- [ ] PRD success criteria cross-check: all v1 boxes achievable after issues 01–03 + this issue.

## Out of scope

- Actually creating Streamlit Cloud account (human step — document only)
- LinkedIn post copy
- Custom domain

## Depends on

- Issues 01, 02, 03 complete
