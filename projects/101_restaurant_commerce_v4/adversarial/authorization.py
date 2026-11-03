"""Bidirectional staff and customer-capability attacks against the live application."""

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from load_contract import validate_target

p = argparse.ArgumentParser()
p.add_argument("--config", required=True, type=Path)
p.add_argument("--output", required=True, type=Path)
a = p.parse_args()
c = json.loads(a.config.read_text())
validate_target(c, a.config)
a.output.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, c["installed"])
from world_model.restaurant_commerce.db import make_engine, session_factory  # noqa: E402
from world_model.restaurant_commerce.staff import provision  # noqa: E402

engine = make_engine(c["database_url"])
username = "other." + uuid.uuid4().hex[:12]
with session_factory(engine)() as session:
    provision(
        session,
        username,
        c["staff_password"],
        c["business_ids"][1],
        "manager",
        actor="synthetic-authorization-test",
    )
engine.dispose()
checks = []
result = dict(
    execution="PARTIAL",
    outcome="FAIL",
    start=datetime.now(UTC).isoformat(),
    revision=c["revision"],
    target=c["base_url"],
    command=[sys.executable, *sys.argv],
)
try:
    with httpx.Client(base_url=c["base_url"], trust_env=False, timeout=15) as h:
        h.post(
            "/api/staff/login",
            json=dict(username=username, password=c["staff_password"]),
            headers={"X-101-Login": "1"},
        ).raise_for_status()
        me = h.get("/api/staff/me")
        me.raise_for_status()
        other = {
            "Cookie": "commerce_staff=" + h.cookies["commerce_staff"],
            "X-101-CSRF": me.json()["csrf"],
        }
        h.cookies.clear()
        for actor, headers, own, foreign in [
            ("A", c["single_staff_headers"], 0, 1),
            ("B", other, 1, 0),
        ]:
            for index, status in [(own, 200), (foreign, 403)]:
                response = h.get(
                    "/api/operator/restaurants/" + c["business_ids"][index] + "/orders",
                    headers=headers,
                )
                checks.append(
                    dict(
                        actor=actor,
                        resource_business=index,
                        status=response.status_code,
                        expected=status,
                    )
                )
        assert all(row["status"] == row["expected"] for row in checks)
        orders = []
        for i, business in enumerate(c["business_ids"]):
            store = h.get("/api/restaurants/" + business + "/storefront").json()
            item = next(
                x
                for m in store["menus"]
                for cat in m["categories"]
                for x in cat["items"]
                if not x["modifier_groups"]
            )
            response = h.post(
                "/api/restaurants/" + business + "/orders",
                json=dict(
                    customer=dict(name="Authorization synthetic", phone="300555060" + str(i)),
                    items=[dict(menu_item_id=item["id"], quantity=1, modifiers=[])],
                    idempotency_key=uuid.uuid4().hex,
                ),
            )
            response.raise_for_status()
            orders.append(response.json())
        for i, order in enumerate(orders):
            for label, headers, status in [
                ("own", {"X-101-Order-Token": order["access_token"]}, 200),
                ("other", {"X-101-Order-Token": orders[1 - i]["access_token"]}, 401),
                ("anonymous", {}, 401),
            ]:
                response = h.get("/api/orders/" + order["id"], headers=headers)
                checks.append(
                    dict(customer=i, credential=label, status=response.status_code, expected=status)
                )
                assert response.status_code == status, (
                    f"{label}: expected {status}, got {response.status_code}"
                )
        response = h.patch(
            "/api/operator/orders/" + orders[0]["id"], headers=other, json={"status": "cancelled"}
        )
        assert response.status_code == 403
        checks.append(dict(actor="B", action="cancel A order", status=403))
        response = h.get(
            "/api/orders/" + orders[0]["id"],
            headers={"X-101-Order-Token": orders[0]["access_token"]},
        )
        assert response.json()["status"] != "cancelled"
        checks.append(dict(action="denied write did not cancel order", passed=True))
        result.update(execution="COMPLETE", outcome="PASS")
except Exception as exc:
    result.update(error_class=type(exc).__name__, error=str(exc))
finally:
    result.update(end=datetime.now(UTC).isoformat(), checks=checks, executed=len(checks))
    (a.output / "receipt.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result))
raise SystemExit(0 if result["outcome"] == "PASS" else 1)
