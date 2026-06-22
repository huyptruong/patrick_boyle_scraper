# Patrick Boyle YouTube Scraper

1. `python scrape_metadata.py` → `data/videos.csv`
2. `python calibrate.py` → calibrate click positions (once per machine/monitor)
3. `python extract_summaries.py` → `data/summaries.csv`

**Platform:** macOS or Windows for browser UI extraction. Metadata scraper works anywhere.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Brave signed into YouTube. In Brave settings, turn off **Continue where you left off** so each extract run starts fresh.

Grant Accessibility to Terminal/Cursor (macOS; needed for calibration and extract).

## First time setup

Run these once on a new machine:

```bash
python scrape_metadata.py --max-videos 5
python calibrate.py
python extract_summaries.py --max-videos 1
```

Then scrape the full channel and extract the rest when ready.

## Regular use

```bash
python scrape_metadata.py
python extract_summaries.py --skip-existing
python export_combined.py
```

### Study slice (one month at a time)

Process a single calendar month (`YYYY-MM`). Re-running the same slice asks whether to refresh; a new slice appends without touching other months.

```bash
# This week — June 2026
python scrape_metadata.py --slice 2026-06
python extract_summaries.py --slice 2026-06

# Preview before Brave opens
python scrape_metadata.py --slice 2026-06 --dry-run
python extract_summaries.py --slice 2026-06 --dry-run

# Fill gaps without re-extracting the whole month
python extract_summaries.py --slice 2026-06 --skip-existing
```

Open `data/summaries.csv`, check what's missing, hand-fill if needed, then move on (e.g. `--slice 2026-05` for backfill).

Other useful commands:

```bash
python extract_summaries.py --retry-failed    # re-run ids in data/failed_ids.txt
python extract_summaries.py --dry-run         # preview without opening Brave
python scrape_metadata.py --merge             # refresh metadata without wiping old rows
```

Terminal shows steps 1–10 per video, then `Saved summary (N chars)`. Progress estimates appear during batch runs.

## Calibrate once (maximized Brave on your screen)

Walk through one sample Patrick Boyle video and save where to click on your screen.

Sample video (steps 2–6): `https://www.youtube.com/watch?v=wKXgeNwNRJ4` (same URL as `SAMPLE_CALIBRATION_VIDEO` in `scraper/config.py`)

```bash
python calibrate.py
```

**You open and maximize Brave yourself.** A small corner HUD guides each target (address bar, pause, Ask, summarize, summary box, copy):

1. **Prep** — read what to do in Brave in the HUD; set up at your own pace.
2. **Capture** — click **Start**, hover over the target (do not click), and hold still while the HUD counts down 10 seconds (Escape or close the HUD to cancel).

On macOS with Homebrew Python, install Tk if calibration fails to start: `brew install python-tk@3.12` (match your Python version).

Click positions live in `data/click_positions.json` (machine-specific; gitignored). Run `python calibrate.py --recalibrate` after a new monitor or if clicks drift.

## Troubleshooting

**Empty clipboard / “Copy returned empty text”**
Increase `after_summarize` or `after_copy` in `EXTRACT_WAITS` at the top of `scraper/brave_extract.py`, or run with `--slow`.

**Extract stops mid-run**
Do not move the mouse to the screen corner during a run — pyautogui treats that as an emergency stop (failsafe).

**Clicks land in the wrong place**
Re-run `python calibrate.py --recalibrate` after a monitor change, resolution change, or Brave layout update. Brave must be maximized.

**Calibration HUD does not capture the mouse (macOS)**
Grant Accessibility permission to Terminal or Cursor in System Settings → Privacy & Security → Accessibility.

**Some videos keep failing**
Check `data/run.log` for timestamps and errors. Failed ids are saved to `data/failed_ids.txt` — retry with `python extract_summaries.py --retry-failed`.

## Project layout

**What you run** (repo root — start here):

| Script | What it does |
|--------|----------------|
| `scrape_metadata.py` | Pull YouTube metadata → `data/videos.csv` |
| `calibrate.py` | One-time click calibration (once per machine/monitor) |
| `extract_summaries.py` | Batch extract summaries → `data/summaries.csv` |
| `export_combined.py` | Join videos + summaries → `data/videos_with_summaries.csv` |

**Engine room** (`scraper/` — open only when debugging):

| File | What it does |
|------|----------------|
| `scraper/brave_extract.py` | Brave clicks for one video; tune `EXTRACT_WAITS` here |
| `scraper/slice.py` | Parse `--slice YYYY-MM`, filter by `upload_date`, merge/replace rules |
| `scraper/extract_plan.py` | Which videos to extract (`--skip-existing`, filters) |
| `scraper/config.py` | Paths, CSV columns, platform checks |
| `scraper/csv_io.py` | Read/write CSV files |
| `scraper/run_log.py` | Append-only log → `data/run.log` |

```
YOU RUN:     scrape_metadata → calibrate → extract_summaries → export_combined

EXTRACT:     extract_summaries.py  →  loop over videos
                 ├── scraper/extract_plan.py   which videos?
                 └── scraper/brave_extract.py  click Brave once
```

## Files

| File | Purpose |
|------|---------|
| `scraper/config.py` | Paths, CSV columns, platform checks, click-position validation |
| `calibrate.py` | One-time calibration wizard → `click_positions.json` |
| `scrape_metadata.py` | Pull YouTube metadata → `videos.csv` |
| `scraper/brave_extract.py` | Brave UI automation for one video summary |
| `scraper/extract_plan.py` | Which videos to extract (filters, skip-existing) |
| `extract_summaries.py` | Batch extract loop → `summaries.csv` |
| `export_combined.py` | Join videos + summaries → `videos_with_summaries.csv` |
| `scraper/csv_io.py` | Read/write CSVs (paths and columns defined in `scraper/config.py`) |
| `scraper/run_log.py` | Append-only extract log → `data/run.log` |

## Tests

```bash
pytest -v
```

Tune wait times in `EXTRACT_WAITS` at the top of `scraper/brave_extract.py`, or run with `--slow` / `--wait-multiplier 2`.
