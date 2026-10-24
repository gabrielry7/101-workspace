#!/usr/bin/env python3
"""
Cheap Google Maps UI probe for:
  - Google's returned place name
  - whether Google visibly marks the place as permanently/temporarily closed

This intentionally does NOT try to bypass CAPTCHAs, bot challenges, consent walls,
or other access controls. If Google does not return a clean place panel, the row
is recorded as UNKNOWN/BLOCKED rather than guessed.

Input CSV default columns:
    source_id,name,lat,lon

Example:
    1,lepimp bar,4.6562411,-74.0588202
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sqlite3
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


PERMANENTLY_CLOSED_PHRASES = (
    "permanently closed",
    "closed permanently",
    "cerrado permanentemente",
    "cerrada permanentemente",
    "cerrado de forma permanente",
    "cerrada de forma permanente",
)

TEMPORARILY_CLOSED_PHRASES = (
    "temporarily closed",
    "closed temporarily",
    "cerrado temporalmente",
    "cerrada temporalmente",
)

BLOCKED_PHRASES = (
    "unusual traffic",
    "our systems have detected unusual traffic",
    "not a robot",
    "recaptcha",
    "before you continue to google",
)

# Common UI labels that help distinguish a real place panel from a search/list page.
PLACE_PANEL_HINTS = (
    "directions",
    "save",
    "nearby",
    "send to phone",
    "share",
    "indicaciones",
    "guardar",
    "cerca",
    "enviar al teléfono",
    "compartir",
)


@dataclass
class ProbeResult:
    source_id: str
    query_name: str
    query_lat: float
    query_lon: float
    google_name: Optional[str]
    status: str
    place_panel_loaded: bool
    final_url: Optional[str]
    checked_at: str
    error: Optional[str] = None

    @property
    def permanently_closed(self) -> Optional[bool]:
        if self.status == "CLOSED_PERMANENTLY":
            return True
        if self.status in ("CLOSED_TEMPORARILY", "OPEN_OR_UNMARKED"):
            return False
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").strip().lower()
    return " ".join(value.split())


def cache_key(name: str, lat: float, lon: float) -> str:
    # Coordinates rounded only for cache identity, not for the actual query.
    raw = f"{normalize_text(name)}|{lat:.7f}|{lon:.7f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_maps_search_url(name: str, lat: float, lon: float) -> str:
    # Search query includes both name and coordinates so the browser asks Google
    # for the business near that exact location.
    query = quote_plus(f"{name} {lat:.7f},{lon:.7f}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def classify_body_text(body_text: str, place_panel_loaded: bool) -> str:
    text = normalize_text(body_text)

    if any(p in text for p in BLOCKED_PHRASES):
        return "BLOCKED"

    if any(p in text for p in PERMANENTLY_CLOSED_PHRASES):
        return "CLOSED_PERMANENTLY"

    if any(p in text for p in TEMPORARILY_CLOSED_PHRASES):
        return "CLOSED_TEMPORARILY"

    # Absence of a closure phrase is only meaningful when a real place panel
    # appears to have loaded.
    if place_panel_loaded:
        return "OPEN_OR_UNMARKED"

    return "UNKNOWN"


def init_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            cache_key TEXT PRIMARY KEY,
            source_id TEXT,
            query_name TEXT NOT NULL,
            query_lat REAL NOT NULL,
            query_lon REAL NOT NULL,
            google_name TEXT,
            status TEXT NOT NULL,
            permanently_closed INTEGER,
            place_panel_loaded INTEGER NOT NULL,
            final_url TEXT,
            checked_at TEXT NOT NULL,
            error TEXT
        )
        """
    )
    conn.commit()
    return conn


def db_get(conn: sqlite3.Connection, key: str) -> Optional[ProbeResult]:
    row = conn.execute(
        """
        SELECT source_id, query_name, query_lat, query_lon, google_name, status,
               place_panel_loaded, final_url, checked_at, error
        FROM results
        WHERE cache_key = ?
        """,
        (key,),
    ).fetchone()

    if not row:
        return None

    return ProbeResult(
        source_id=row[0] or "",
        query_name=row[1],
        query_lat=row[2],
        query_lon=row[3],
        google_name=row[4],
        status=row[5],
        place_panel_loaded=bool(row[6]),
        final_url=row[7],
        checked_at=row[8],
        error=row[9],
    )


def db_put(conn: sqlite3.Connection, key: str, result: ProbeResult) -> None:
    perm = result.permanently_closed
    conn.execute(
        """
        INSERT INTO results (
            cache_key, source_id, query_name, query_lat, query_lon,
            google_name, status, permanently_closed, place_panel_loaded,
            final_url, checked_at, error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            source_id=excluded.source_id,
            query_name=excluded.query_name,
            query_lat=excluded.query_lat,
            query_lon=excluded.query_lon,
            google_name=excluded.google_name,
            status=excluded.status,
            permanently_closed=excluded.permanently_closed,
            place_panel_loaded=excluded.place_panel_loaded,
            final_url=excluded.final_url,
            checked_at=excluded.checked_at,
            error=excluded.error
        """,
        (
            key,
            result.source_id,
            result.query_name,
            result.query_lat,
            result.query_lon,
            result.google_name,
            result.status,
            None if perm is None else int(perm),
            int(result.place_panel_loaded),
            result.final_url,
            result.checked_at,
            result.error,
        ),
    )
    conn.commit()


def export_csv(conn: sqlite3.Connection, output_path: Path) -> None:
    rows = conn.execute(
        """
        SELECT source_id, query_name, query_lat, query_lon, google_name, status,
               permanently_closed, place_panel_loaded, final_url, checked_at, error
        FROM results
        ORDER BY rowid
        """
    ).fetchall()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")

    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "source_id",
                "query_name",
                "query_lat",
                "query_lon",
                "google_name",
                "status",
                "permanently_closed",
                "place_panel_loaded",
                "final_url",
                "checked_at",
                "error",
            ]
        )
        for row in rows:
            row = list(row)
            # Convert SQLite null/0/1 to a readable tri-state.
            if row[6] is None:
                row[6] = ""
            else:
                row[6] = "true" if row[6] else "false"
            row[7] = "true" if row[7] else "false"
            writer.writerow(row)

    tmp.replace(output_path)


def read_input(
    path: Path,
    id_col: str,
    name_col: str,
    lat_col: str,
    lon_col: str,
) -> Iterable[tuple[str, str, float, float]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {name_col, lat_col, lon_col}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Missing required CSV columns: {', '.join(sorted(missing))}. "
                f"Found: {reader.fieldnames}"
            )

        for i, row in enumerate(reader, start=1):
            name = (row.get(name_col) or "").strip()
            if not name:
                continue

            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
            except (TypeError, ValueError):
                print(f"[skip] row {i}: invalid coordinates", file=sys.stderr)
                continue

            source_id = (row.get(id_col) or "").strip() if id_col in row else ""
            if not source_id:
                source_id = str(i)

            yield source_id, name, lat, lon


def get_google_name(page) -> Optional[str]:
    selectors = [
        "h1.DUwDvf",
        'h1[class*="DUwDvf"]',
        "h1",
    ]

    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() and loc.is_visible(timeout=1000):
                text = loc.inner_text(timeout=1500).strip()
                if text:
                    return text
        except Exception:
            pass
    return None


def looks_like_place_panel(page, google_name: Optional[str], body_text: str) -> bool:
    if not google_name:
        return False

    url = page.url.lower()
    if "/maps/place/" in url:
        return True

    text = normalize_text(body_text)
    hint_count = sum(1 for hint in PLACE_PANEL_HINTS if hint in text)
    if hint_count >= 2:
        return True

    # Stable-ish Maps data-item ids often exist on a loaded place details panel.
    selectors = [
        '[data-item-id="address"]',
        '[data-item-id^="phone:tel:"]',
        '[data-item-id="authority"]',
    ]
    for selector in selectors:
        try:
            if page.locator(selector).count() > 0:
                return True
        except Exception:
            pass

    return False


def probe_one(page, source_id: str, name: str, lat: float, lon: float, timeout_ms: int) -> ProbeResult:
    url = build_maps_search_url(name, lat, lon)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        # Maps is an app: wait for either a heading or enough app time to render.
        try:
            page.locator("h1").first.wait_for(state="visible", timeout=min(timeout_ms, 12000))
        except PlaywrightTimeoutError:
            page.wait_for_timeout(2500)

        body_text = page.locator("body").inner_text(timeout=5000)
        google_name = get_google_name(page)
        panel_loaded = looks_like_place_panel(page, google_name, body_text)
        status = classify_body_text(body_text, panel_loaded)

        return ProbeResult(
            source_id=source_id,
            query_name=name,
            query_lat=lat,
            query_lon=lon,
            google_name=google_name,
            status=status,
            place_panel_loaded=panel_loaded,
            final_url=page.url,
            checked_at=now_iso(),
        )

    except Exception as exc:
        return ProbeResult(
            source_id=source_id,
            query_name=name,
            query_lat=lat,
            query_lon=lon,
            google_name=None,
            status="UNKNOWN",
            place_panel_loaded=False,
            final_url=getattr(page, "url", None),
            checked_at=now_iso(),
            error=f"{type(exc).__name__}: {exc}",
        )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Probe Google Maps UI for returned name and visible closure status."
    )
    ap.add_argument("input_csv", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("maps_status_results.csv"))
    ap.add_argument("--db", type=Path, default=Path("maps_status_cache.sqlite3"))
    ap.add_argument(
        "--profile-dir",
        type=Path,
        default=Path(".maps-browser-profile"),
        help="Persistent Chromium profile directory",
    )
    ap.add_argument("--id-col", default="source_id")
    ap.add_argument("--name-col", default="name")
    ap.add_argument("--lat-col", default="lat")
    ap.add_argument("--lon-col", default="lon")
    ap.add_argument("--min-delay", type=float, default=2.0)
    ap.add_argument("--max-delay", type=float, default=5.0)
    ap.add_argument("--timeout-ms", type=int, default=30000)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process this many input rows (useful for canaries)",
    )
    args = ap.parse_args()

    if args.min_delay < 0 or args.max_delay < args.min_delay:
        ap.error("Require 0 <= min-delay <= max-delay")

    conn = init_db(args.db)
    rows = list(
        read_input(
            args.input_csv,
            args.id_col,
            args.name_col,
            args.lat_col,
            args.lon_col,
        )
    )

    if args.limit is not None:
        rows = rows[: args.limit]

    args.profile_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    cached = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(args.profile_dir),
            headless=args.headless,
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
        )
        page = context.pages[0] if context.pages else context.new_page()

        for idx, (source_id, name, lat, lon) in enumerate(rows, start=1):
            key = cache_key(name, lat, lon)
            existing = None if args.refresh else db_get(conn, key)

            if existing is not None:
                cached += 1
                print(
                    f"[{idx}/{len(rows)}] cache  {name!r} -> "
                    f"{existing.google_name!r} | {existing.status}"
                )
                continue

            result = probe_one(
                page=page,
                source_id=source_id,
                name=name,
                lat=lat,
                lon=lon,
                timeout_ms=args.timeout_ms,
            )
            db_put(conn, key, result)
            export_csv(conn, args.output)
            processed += 1

            print(
                f"[{idx}/{len(rows)}] probe  {name!r} -> "
                f"{result.google_name!r} | {result.status}"
            )

            # If Google presents a block/challenge, stop instead of hammering.
            if result.status == "BLOCKED":
                print(
                    "\nGoogle presented a challenge/block page. Stopping cleanly.\n"
                    "The completed rows are checkpointed. Resolve it manually in the "
                    "persistent browser profile or wait, then rerun.",
                    file=sys.stderr,
                )
                break

            if idx < len(rows):
                time.sleep(random.uniform(args.min_delay, args.max_delay))

        context.close()

    export_csv(conn, args.output)
    conn.close()

    print(
        f"\nDone. New probes: {processed}; cache hits: {cached}. "
        f"CSV: {args.output}; DB: {args.db}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
