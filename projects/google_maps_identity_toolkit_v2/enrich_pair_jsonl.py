#!/usr/bin/env python3
"""Add explainable review-aid features to a pair-review queue.

Input may be JSONL or a JSON array. The script preserves every original field and
adds a top-level `review_aids` object. It tries several common pair schemas; when
yours differs, provide --a-path/--b-path to the objects representing each source.

This is deliberately offline: no Google calls and no canonical writes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from identity_aids import pair_review_aids

SIDE_A_CANDIDATES = ("source_1", "source1", "source_a", "record_a", "left", "a")
SIDE_B_CANDIDATES = ("source_2", "source2", "source_b", "record_b", "right", "b")


def get_path(obj: Any, path: str | None) -> Any:
    if not path:
        return obj
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def auto_side(obj: dict, candidates: tuple[str, ...]) -> dict | None:
    for key in candidates:
        value = obj.get(key)
        if isinstance(value, dict):
            return value
    return None


def first(obj: dict | None, *keys: str) -> Any:
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return None


def coords(side: dict | None) -> tuple[Any, Any]:
    if not isinstance(side, dict):
        return None, None
    lat = first(side, "lat", "latitude")
    lon = first(side, "lon", "lng", "longitude")
    if lat is not None and lon is not None:
        return lat, lon
    for key in ("coordinates", "coordinate", "marker", "source_marker", "location"):
        value = side.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return value[0], value[1]
        if isinstance(value, dict):
            lat2 = first(value, "lat", "latitude")
            lon2 = first(value, "lon", "lng", "longitude")
            if lat2 is not None and lon2 is not None:
                return lat2, lon2
    return None, None


def enrich(record: dict, a_path: str | None, b_path: str | None) -> dict:
    a = get_path(record, a_path) if a_path else auto_side(record, SIDE_A_CANDIDATES)
    b = get_path(record, b_path) if b_path else auto_side(record, SIDE_B_CANDIDATES)
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise ValueError(
            "Could not find source pair objects. Use --a-path and --b-path. "
            f"Top-level keys: {sorted(record.keys())}"
        )

    lat_a, lon_a = coords(a)
    lat_b, lon_b = coords(b)
    result = dict(record)
    result["review_aids"] = pair_review_aids(
        name_a=first(a, "name", "display_name", "title"),
        name_b=first(b, "name", "display_name", "title"),
        address_a=first(a, "address", "formatted_address", "street_address"),
        address_b=first(b, "address", "formatted_address", "street_address"),
        phone_a=first(a, "phone", "telephone", "phone_number"),
        phone_b=first(b, "phone", "telephone", "phone_number"),
        domain_a=first(a, "domain", "website", "url"),
        domain_b=first(b, "domain", "website", "url"),
        category_a=first(a, "native_category", "category", "categories", "taxonomy"),
        category_b=first(b, "native_category", "category", "categories", "taxonomy"),
        lat_a=lat_a,
        lon_a=lon_a,
        lat_b=lat_b,
        lon_b=lon_b,
    )
    return result


def read_records(path: Path) -> Iterable[dict]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("JSON input must be an array or JSONL")
        yield from data
        return
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Line {lineno} is not a JSON object")
        yield value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--a-path", help="Dotted path to source A object")
    ap.add_argument("--b-path", help="Dotted path to source B object")
    args = ap.parse_args()

    count = 0
    with args.output.open("w", encoding="utf-8") as out:
        for record in read_records(args.input):
            enriched = enrich(record, args.a_path, args.b_path)
            out.write(json.dumps(enriched, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    print(f"Wrote {count} enriched pairs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
