"""Live finite-inventory race with PostgreSQL and independent provider verification."""

import argparse
import json
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fixture_state import business_inputs

p = argparse.ArgumentParser()
p.add_argument("--config", required=True, type=Path)
p.add_argument("--output", required=True, type=Path)
a = p.parse_args()
c = json.loads(a.config.read_text())
a.output.mkdir(parents=True, exist_ok=False)
started = datetime.now(UTC).isoformat()
scoped = {**c, "business_ids": [c["business_ids"][1]]}
result = dict(
    execution="PARTIAL",
    outcome="FAIL",
    start=started,
    revision=c["revision"],
    wheel_sha256=c.get("wheel_sha256"),
    command=[sys.executable, *sys.argv],
    target=c["base_url"],
)
try:
    with business_inputs(scoped, a.config):
        from sqlalchemy import create_engine, select
        from world_model.restaurant_commerce.models import ItemStock, Order, Payment

        business = scoped["business_ids"][0]
        root = c["base_url"] + "/api/restaurants/" + business
        with httpx.Client(trust_env=False, timeout=20) as h:
            store = h.get(root + "/storefront").json()
            item = store["menus"][0]["categories"][0]["items"][0]["id"]
            r = h.put(
                c["base_url"] + "/api/operator/restaurants/" + business + "/stock/" + item,
                headers=c["dual_staff_headers"],
                json=dict(expected_version=0, remaining=2, sold_out=False, reason="Synthetic race"),
            )
            r.raise_for_status()
            prefix = "stock-race-" + uuid.uuid4().hex
            bodies = [
                dict(
                    customer=dict(name="Synthetic race", phone="3005550400"),
                    items=[dict(menu_item_id=item, quantity=1, modifiers=[])],
                    idempotency_key=prefix + "-" + str(i),
                )
                for i in range(10)
            ]
            with ThreadPoolExecutor(max_workers=10) as pool:
                replies = list(pool.map(lambda body: h.post(root + "/orders", json=body), bodies))
            winners = [
                (b, r.json()) for b, r in zip(bodies, replies, strict=True) if r.status_code == 200
            ]
            assert len(winners) == 2, [r.status_code for r in replies]
            assert all(r.status_code in (200, 422) for r in replies)
            for body, order in winners:
                replay = h.post(root + "/orders", json=body)
                assert replay.status_code == 200 and replay.json()["id"] == order["id"]
            engine = create_engine(c["database_url"])
            with engine.connect() as conn:
                remaining = conn.scalar(
                    select(ItemStock.remaining).where(ItemStock.item_id == item)
                )
                orders = list(
                    conn.scalars(select(Order.id).where(Order.idempotency_key.startswith(prefix)))
                )
                payments = list(
                    conn.scalars(select(Payment.order_id).where(Payment.order_id.in_(orders)))
                )
            engine.dispose()
            effects = [
                e
                for e in h.get(c["provider_direct_url"] + "/records").json()["effects"]
                if prefix in e["key"]
            ]
            assert (
                remaining == 0
                and len(orders) == len(set(orders)) == len(payments) == len(effects) == 2
            )
            result.update(
                execution="COMPLETE",
                outcome="PASS",
                attempted_buyers=10,
                accepted_orders=2,
                rejected_requests=8,
                remaining_stock=remaining,
                payments=len(payments),
                provider_effects=len(effects),
                same_order_replays=2,
            )
except Exception as exc:
    result["error_class"] = type(exc).__name__
    result["error"] = str(exc)
finally:
    result["end"] = datetime.now(UTC).isoformat()
    (a.output / "receipt.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result))
raise SystemExit(0 if result["outcome"] == "PASS" else 1)
