from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from world_model.restaurant_commerce.cache import TTLCache
from world_model.restaurant_commerce.db import init_schema, make_engine, session_factory
from world_model.restaurant_commerce.schemas import CartItemIn, ModifierSelectionIn
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * p)))
    return ordered[idx]


def timed(iterations: int, fn):
    values: list[float] = []
    started = time.perf_counter()
    for _ in range(iterations):
        one = time.perf_counter()
        fn()
        values.append((time.perf_counter() - one) * 1000)
    elapsed = time.perf_counter() - started
    return {
        "iterations": iterations,
        "elapsed_seconds": round(elapsed, 4),
        "ops_per_second": round(iterations / elapsed, 2) if elapsed else 0.0,
        "mean_ms": round(statistics.fmean(values), 4),
        "p50_ms": round(percentile(values, 0.50), 4),
        "p95_ms": round(percentile(values, 0.95), 4),
        "p99_ms": round(percentile(values, 0.99), 4),
        "max_ms": round(max(values), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline deterministic V4 service hot-path benchmark")
    parser.add_argument("--storefront-iterations", type=int, default=20_000)
    parser.add_argument("--quote-iterations", type=int, default=2_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="101-commerce-v4-") as tmp:
        engine = make_engine(f"sqlite:///{Path(tmp) / 'bench.db'}")
        init_schema(engine)
        SessionLocal = session_factory(engine)
        cache: TTLCache = TTLCache(ttl_seconds=300, max_entries=128)
        with SessionLocal() as session:
            seed_demo(session)
            service = RestaurantCommerceService(session, storefront_cache=cache)
            storefront = service.storefront(DEMO_BUSINESS_ID)
            item = next(
                item
                for menu in storefront.menus
                for category in menu.categories
                for item in category.items
                if item.name == "Smash 101"
            )
            term = next(group for group in item.modifier_groups if group.name == "Término")
            cart = [
                CartItemIn(
                    menu_item_id=item.id,
                    quantity=2,
                    modifiers=[
                        ModifierSelectionIn(group_id=term.id, option_ids=[term.options[0].id])
                    ],
                )
            ]

            storefront_result = timed(
                max(1, args.storefront_iterations),
                lambda: service.storefront(DEMO_BUSINESS_ID),
            )
            quote_result = timed(
                max(1, args.quote_iterations),
                lambda: service.quote(DEMO_BUSINESS_ID, cart),
            )

        engine.dispose()

    result = {
        "benchmark": "restaurant-commerce-v4-offline",
        "storefront_cached": storefront_result,
        "quote_server_side": quote_result,
        "notes": [
            "Single-process local benchmark; not a production capacity forecast.",
            "No external network/provider calls.",
            "Storefront path is warm shared TTL-cache; quote path hits SQLite and performs authoritative server pricing.",
        ],
    }
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
