# Google Maps status probe

A deliberately narrow browser-based probe for two visible Google Maps fields:

1. the place name Google returns;
2. whether the place is visibly marked **permanently closed** or **temporarily closed**.

It does **not** use the paid Places API and it does not attempt to bypass CAPTCHAs,
bot challenges, consent walls, or rate limits. If the browser does not get a clean
place panel, the result is `UNKNOWN` or `BLOCKED` rather than guessed.

## Input

CSV with at least:

```csv
source_id,name,lat,lon
1,lepimp bar,4.6562411,-74.0588202
```

Column names can be changed with CLI flags.

## Install on Arch Linux

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## First canary

Run headful first so you can see exactly what Google is returning:

```bash
python maps_status_probe.py sample_input.csv --limit 5
```

Default behavior:

- one browser;
- persistent profile in `.maps-browser-profile/`;
- requests are sequential;
- 2–5 second randomized delay between places;
- every completed record is immediately checkpointed to SQLite;
- a CSV export is rewritten atomically after each new result;
- reruns reuse cached results;
- if a challenge/block page appears, the runner stops instead of continuing.

Output:

```csv
source_id,query_name,query_lat,query_lon,google_name,status,permanently_closed,place_panel_loaded,...
1,lepimp bar,4.6562411,-74.0588202,lepimp bar,CLOSED_PERMANENTLY,true,true,...
```

Possible statuses:

- `CLOSED_PERMANENTLY`
- `CLOSED_TEMPORARILY`
- `OPEN_OR_UNMARKED`
- `UNKNOWN`
- `BLOCKED`

`OPEN_OR_UNMARKED` does **not** mean that Google independently verified the
business is operating. It means a proper place panel loaded and no visible closure
label was found.

## Larger run

```bash
python maps_status_probe.py bogota_candidates.csv \
  -o bogota_google_status.csv \
  --db bogota_google_status.sqlite3 \
  --min-delay 2 \
  --max-delay 5
```

If your columns are named differently:

```bash
python maps_status_probe.py businesses.csv \
  --id-col business_id \
  --name-col business_name \
  --lat-col latitude \
  --lon-col longitude
```

Headless mode:

```bash
python maps_status_probe.py businesses.csv --headless
```

For initial tests, headful is better because Maps UI changes are visible.

## Refreshing old records

By default, an identical `(name, lat, lon)` reuses the cached row.

To probe it again:

```bash
python maps_status_probe.py businesses.csv --refresh
```

## Files

- `maps_status_probe.py` — runner
- `maps_status_cache.sqlite3` — durable cache/checkpoint, created at runtime
- `maps_status_results.csv` — export, created at runtime
- `.maps-browser-profile/` — persistent Chromium session, created at runtime

## Recommended 101 workflow

Do not immediately run the whole universe. Start with 25–50 known examples:

- known permanently closed;
- known operating;
- renamed businesses;
- chain branches;
- ambiguous names;
- places inside malls/buildings.

Measure whether the returned Google name is actually the intended entity before
using the status downstream. A closure label is only useful if the entity match is
correct.
