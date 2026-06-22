# Patrick Boyle Scraper — domain glossary

Terms this project uses. Update as decisions land during design work.

## Pipeline

- **Metadata scrape** — `scrape_metadata.py` fetches video info from YouTube into `data/videos.csv` (id, title, upload_date, etc.). Network-based; reliable.
- **Extract run** — `extract_summaries.py` loops videos and copies Brave Ask summaries into `data/summaries.csv`. UI automation; brittle; slow.
- **Calibration** — one-time save of screen click positions (`data/click_positions.json`) per machine/monitor.

## Data files

- **Video** — one row in `videos.csv`, keyed by YouTube `id`. `upload_date` is `YYYYMMDD` from yt-dlp.
- **Summary** — one row in `summaries.csv`: `id` + `summary` text from Brave Ask.
- **Failed id** — a video id logged to `data/failed_ids.txt` after an extract attempt failed (retry with `--retry-failed`).

## Study slices

- **Study slice** — one calendar month (`YYYY-MM`) passed as `--slice` on scrape and extract. Forward months as they happen; older months backfilled when you have time.
- **Time-bounded pull** — only videos whose `upload_date` falls in the slice month are scraped or extracted.
- **Slice refresh** — re-running the same `--slice` shows `Refresh? [y/N]`. Yes replaces that month only; other months stay untouched.
- **Slice append** — running a **new** `--slice` **adds** that month's rows; existing months stay as-is.
