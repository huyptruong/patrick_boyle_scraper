# ADR-0001: Study-slice CSV merge semantics

## Status

Accepted (2026-06-22)

## Context

The user processes one calendar month at a time (`YYYY-MM`). `videos.csv` and `summaries.csv` accumulate over weeks. Re-running the same month should refresh that month only; running a new month should append without disturbing prior months.

## Decision

Both `scrape_metadata.py` and `extract_summaries.py` accept `--slice YYYY-MM` (strict format; invalid → error).

**videos.csv (metadata scrape)**

- Filter discovered/fetched videos to `upload_date` in the slice month (`YYYYMMDD` prefix match).
- If the slice month already has rows in `videos.csv`, print a warning and prompt to refresh (unless `--yes` / non-interactive flag).
- **Refresh:** remove existing rows for that slice month, write new rows for that month, keep all other rows.
- **New slice:** merge in rows for that month; do not remove other months.

**summaries.csv (extract)**

- Only extract videos in `videos.csv` whose `upload_date` falls in the slice month.
- Same refresh vs append semantics when re-running the same slice (replace summary rows for that month's video ids; keep other months).
- Interactive prompt on re-run: slice already extracted — refresh? Default **no** (`[y/N]`). Pass `--yes` only if we add it later for automation; for now interactive only per user preference.

**CLI**

- Flag: `--slice YYYY-MM` (strict; invalid format → error).
- Re-run prompt: interactive in terminal; user has full context as sole operator.

## Consequences

- User does not need a separate "full catalog" step; each `--slice` scrape walks the channel and keeps matching rows (backfill of old months may be slow).
- User is responsible for not overlapping/conflicting manual edits; tool replaces by `upload_date` month / video id, not a database transaction.
