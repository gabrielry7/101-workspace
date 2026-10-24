#!/usr/bin/env python3
"""Persistent Playwright probe for Google Maps visible place metadata.

Two lookup modes:
- search: name + coordinates
- place-id: exact Google Place ID URL

This script intentionally does not bypass CAPTCHAs, bot challenges, consent walls,
or other access controls. It stops on a detected block/challenge and records
UNKNOWN when a clean place panel was not observed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import re
import sqlite3
import sys
import time
import unicodedata
from dataclasses import dataclass
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
PLACE_PANEL_HINTS = (
    "directions", "save", "nearby", "send to phone", "share",
    "indicaciones", "guardar", "cerca", "enviar al teléfono", "compartir",
)


@dataclass
class ProbeResult:
    source_id: str
    lookup_type: str
    query_name: Optional[str]
    query_lat: Optional[float]
    query_lon: Optional[float]
    input_place_id: Optional[str]
    google_name: Optional[str]
    status: str
    place_panel_loaded: bool
    visible_address: Optional[str]
    visible_category: Optional[str]
    visible_phone: Optional[str]
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


def build_search_url(name: str, lat: float, lon: float) -> str:
    query = quote_plus(f"{name} {lat:.7f},{lon:.7f}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def build_place_id_url(place_id: str) -> str:
    return f"https://www.google.com/maps/place/?q=place_id:{quote_plus(place_id)}"


def cache_key(*, lookup_type: str, name: Optional[str], lat: Optional[float], lon: Optional[float], place_id: Optional[str]) -> str:
    if lookup_type == "place-id":
        raw = f"place-id|{(place_id or '').strip()}"
    else:
        raw = f"search|{normalize_text(name or '')}|{float(lat):.7f}|{float(lon):.7f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def classify_body_text(body_text: str, place_panel_loaded: bool) -> str:
    text = normalize_text(body_text)
    if any(p in text for p in BLOCKED_PHRASES):
        return "BLOCKED"
    if any(p in text for p in PERMANENTLY_CLOSED_PHRASES):
        return "CLOSED_PERMANENTLY"
    if any(p in text for p in TEMPORARILY_CLOSED_PHRASES):
        return "CLOSED_TEMPORARILY"
    if place_panel_loaded:
        return "OPEN_OR_UNMARKED"
    return "UNKNOWN"


def text_of_first(page, selectors: list[str], timeout: int = 1200) -> Optional[str]:
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() and loc.is_visible(timeout=timeout):
                text = loc.inner_text(timeout=timeout).strip()
                if text:
                    return text
                aria = loc.get_attribute("aria-label")
                if aria:
                    return aria.strip()
        except Exception:
            pass
    return None


def get_google_name(page) -> Optional[str]:
    return text_of_first(page, ["h1.DUwDvf", 'h1[class*="DUwDvf"]', "h1"])


def get_visible_address(page) -> Optional[str]:
    value = text_of_first(page, ['[data-item-id="address"]'])
    if value:
        return re.sub(r"^(address|dirección):\s*", "", value, flags=re.I).strip()
    return None


def get_visible_phone(page) -> Optional[str]:
    value = text_of_first(page, ['[data-item-id^="phone:tel:"]'])
    if value:
        return re.sub(r"^(phone|teléfono):\s*", "", value, flags=re.I).strip()
    return None


def get_visible_category(page) -> Optional[str]:
    # These selectors are intentionally redundant because Maps classes change.
    return text_of_first(
        page,
        [
            'button[jsaction*="pane.rating.category"]',
            'button.DkEaL',
            'div.DkEaL',
        ],
    )


def looks_like_place_panel(page, google_name: Optional[str], body_text: str) -> bool:
    if not google_name:
        return False
    if "/maps/place/" in page.url.lower():
        return True
    text = normalize_text(body_text)
    if sum(1 for hint in PLACE_PANEL_HINTS if hint in text) >= 2:
        return True
    for selector in ('[data-item-id="address"]', '[data-item-id^="phone:tel:"]', '[data-item-id="authority"]'):
        try:
            if page.locator(selector).count() > 0:
                return True
        except Exception:
            pass
    return False


def probe_one(page, *, source_id: str, lookup_type: str, name: Optional[str], lat: Optional[float], lon: Optional[float], place_id: Optional[str], timeout_ms: int) -> ProbeResult:
    if lookup_type == "place-id":
        if not place_id:
            raise ValueError("place-id lookup requires place_id")
        url = build_place_id_url(place_id)
    else:
        if name is None or lat is None or lon is None:
            raise ValueError("search lookup requires name, lat and lon")
        url = build_search_url(name, lat, lon)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
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
            lookup_type=lookup_type,
            query_name=name,
            query_lat=lat,
            query_lon=lon,
            input_place_id=place_id,
            google_name=google_name,
            status=status,
            place_panel_loaded=panel_loaded,
            visible_address=get_visible_address(page) if panel_loaded else None,
            visible_category=get_visible_category(page) if panel_loaded else None,
            visible_phone=get_visible_phone(page) if panel_loaded else None,
            final_url=page.url,
            checked_at=now_iso(),
        )
    except Exception as exc:
        return ProbeResult(
            source_id=source_id,
            lookup_type=lookup_type,
            query_name=name,
            query_lat=lat,
            query_lon=lon,
            input_place_id=place_id,
            google_name=None,
            status="UNKNOWN",
            place_panel_loaded=False,
            visible_address=None,
            visible_category=None,
            visible_phone=None,
            final_url=getattr(page, "url", None),
            checked_at=now_iso(),
            error=f"{type(exc).__name__}: {exc}",
        )


def init_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            cache_key TEXT PRIMARY KEY,
            source_id TEXT,
            lookup_type TEXT NOT NULL,
            query_name TEXT,
            query_lat REAL,
            query_lon REAL,
            input_place_id TEXT,
            google_name TEXT,
            status TEXT NOT NULL,
            permanently_closed INTEGER,
            place_panel_loaded INTEGER NOT NULL,
            visible_address TEXT,
            visible_category TEXT,
            visible_phone TEXT,
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
        SELECT source_id, lookup_type, query_name, query_lat, query_lon,
               input_place_id, google_name, status, place_panel_loaded,
               visible_address, visible_category, visible_phone, final_url,
               checked_at, error
        FROM results WHERE cache_key = ?
        """,
        (key,),
    ).fetchone()
    if not row:
        return None
    return ProbeResult(
        source_id=row[0] or "", lookup_type=row[1], query_name=row[2],
        query_lat=row[3], query_lon=row[4], input_place_id=row[5],
        google_name=row[6], status=row[7], place_panel_loaded=bool(row[8]),
        visible_address=row[9], visible_category=row[10], visible_phone=row[11],
        final_url=row[12], checked_at=row[13], error=row[14],
    )


def db_put(conn: sqlite3.Connection, key: str, r: ProbeResult) -> None:
    perm = r.permanently_closed
    conn.execute(
        """
        INSERT INTO results (
            cache_key, source_id, lookup_type, query_name, query_lat, query_lon,
            input_place_id, google_name, status, permanently_closed,
            place_panel_loaded, visible_address, visible_category, visible_phone,
            final_url, checked_at, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            source_id=excluded.source_id,
            lookup_type=excluded.lookup_type,
            query_name=excluded.query_name,
            query_lat=excluded.query_lat,
            query_lon=excluded.query_lon,
            input_place_id=excluded.input_place_id,
            google_name=excluded.google_name,
            status=excluded.status,
            permanently_closed=excluded.permanently_closed,
            place_panel_loaded=excluded.place_panel_loaded,
            visible_address=excluded.visible_address,
            visible_category=excluded.visible_category,
            visible_phone=excluded.visible_phone,
            final_url=excluded.final_url,
            checked_at=excluded.checked_at,
            error=excluded.error
        """,
        (
            key, r.source_id, r.lookup_type, r.query_name, r.query_lat, r.query_lon,
            r.input_place_id, r.google_name, r.status,
            None if perm is None else int(perm), int(r.place_panel_loaded),
            r.visible_address, r.visible_category, r.visible_phone,
            r.final_url, r.checked_at, r.error,
        ),
    )
    conn.commit()


def export_csv(conn: sqlite3.Connection, path: Path) -> None:
    rows = conn.execute(
        """
        SELECT source_id, lookup_type, query_name, query_lat, query_lon,
               input_place_id, google_name, status, permanently_closed,
               place_panel_loaded, visible_address, visible_category,
               visible_phone, final_url, checked_at, error
        FROM results ORDER BY rowid
        """
    ).fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "lookup_type", "query_name", "query_lat", "query_lon",
            "input_place_id", "google_name", "status", "permanently_closed",
            "place_panel_loaded", "visible_address", "visible_category",
            "visible_phone", "final_url", "checked_at", "error",
        ])
        for row in rows:
            row = list(row)
            row[8] = "" if row[8] is None else ("true" if row[8] else "false")
            row[9] = "true" if row[9] else "false"
            w.writerow(row)
    tmp.replace(path)


def read_input(path: Path, args) -> Iterable[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            source_id = (row.get(args.id_col) or str(i)).strip()
            place_id = (row.get(args.place_id_col) or "").strip() or None
            name = (row.get(args.name_col) or "").strip() or None
            lat = lon = None
            try:
                if row.get(args.lat_col) not in (None, ""):
                    lat = float(row[args.lat_col])
                if row.get(args.lon_col) not in (None, ""):
                    lon = float(row[args.lon_col])
            except ValueError:
                pass

            lookup_type = args.mode
            if lookup_type == "auto":
                lookup_type = "place-id" if place_id else "search"

            if lookup_type == "place-id" and not place_id:
                print(f"[skip] row {i}: no {args.place_id_col}", file=sys.stderr)
                continue
            if lookup_type == "search" and (not name or lat is None or lon is None):
                print(f"[skip] row {i}: search requires name/lat/lon", file=sys.stderr)
                continue
            yield {
                "source_id": source_id, "lookup_type": lookup_type,
                "name": name, "lat": lat, "lon": lon, "place_id": place_id,
            }


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe visible Google Maps place metadata with a persistent browser.")
    ap.add_argument("input_csv", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("google_maps_probe_results.csv"))
    ap.add_argument("--db", type=Path, default=Path("google_maps_probe_cache.sqlite3"))
    ap.add_argument("--profile-dir", type=Path, default=Path(".maps-browser-profile"))
    ap.add_argument("--mode", choices=["auto", "search", "place-id"], default="auto")
    ap.add_argument("--id-col", default="source_id")
    ap.add_argument("--name-col", default="name")
    ap.add_argument("--lat-col", default="lat")
    ap.add_argument("--lon-col", default="lon")
    ap.add_argument("--place-id-col", default="place_id")
    ap.add_argument("--min-delay", type=float, default=2.0)
    ap.add_argument("--max-delay", type=float, default=5.0)
    ap.add_argument("--timeout-ms", type=int, default=30000)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    if args.min_delay < 0 or args.max_delay < args.min_delay:
        ap.error("Require 0 <= min-delay <= max-delay")

    rows = list(read_input(args.input_csv, args))
    if args.limit is not None:
        rows = rows[:args.limit]

    conn = init_db(args.db)
    args.profile_dir.mkdir(parents=True, exist_ok=True)
    processed = cached = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(args.profile_dir),
            headless=args.headless,
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
        )
        page = context.pages[0] if context.pages else context.new_page()

        for idx, item in enumerate(rows, 1):
            key = cache_key(
                lookup_type=item["lookup_type"], name=item["name"], lat=item["lat"],
                lon=item["lon"], place_id=item["place_id"],
            )
            existing = None if args.refresh else db_get(conn, key)
            if existing:
                cached += 1
                print(f"[{idx}/{len(rows)}] cache {item['source_id']} -> {existing.google_name!r} | {existing.status}")
                continue

            result = probe_one(page, timeout_ms=args.timeout_ms, **item)
            db_put(conn, key, result)
            export_csv(conn, args.output)
            processed += 1
            print(f"[{idx}/{len(rows)}] probe {item['source_id']} -> {result.google_name!r} | {result.status}")

            if result.status == "BLOCKED":
                print("Google presented a challenge/block page. Stopping; completed rows are checkpointed.", file=sys.stderr)
                break
            if idx < len(rows):
                time.sleep(random.uniform(args.min_delay, args.max_delay))

        context.close()

    export_csv(conn, args.output)
    conn.close()
    print(f"Done. New probes: {processed}; cache hits: {cached}. CSV: {args.output}; DB: {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
