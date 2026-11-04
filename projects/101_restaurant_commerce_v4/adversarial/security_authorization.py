"""Existing foreign records must be denied without financial/campaign changes."""

import json
from uuid import uuid4

from security_fixtures import Fixtures


def verify(config, output):
    f = Fixtures(config)
    results = []
    try:
        f.http.post(config["provider_url"] + "/control", json={"mode": "paid"}).raise_for_status()
        business, foreign = config["business_ids"]
        # Foreign order really exists and is readable by its own scoped principal.
        store = f.call("GET", f"/api/restaurants/{foreign}/storefront", headers={})
        item = store["menus"][0]["categories"][0]["items"][0]
        other = f.call(
            "POST",
            f"/api/restaurants/{foreign}/orders",
            {
                "customer": {"phone": "3005550789", "name": "Foreign synthetic"},
                "items": [{"menu_item_id": item["id"], "quantity": 1}],
                "idempotency_key": "foreign-" + uuid4().hex,
            },
            headers={},
        )
        own = f.order()
        draft = f.draft()
        draft["customer_ids"] = [config["customer_ids"][1]]
        foreign_campaign = f.call(
            "POST",
            f"/api/operator/restaurants/{foreign}/campaigns",
            draft,
            headers=config["dual_staff_headers"],
        )
        for method, path, body, headers, status in [
            (
                "GET",
                f"/api/finance/restaurants/{foreign}/orders/{other['id']}",
                None,
                f.headers,
                403,
            ),
            (
                "POST",
                f"/api/finance/restaurants/{business}/orders/{other['id']}/refund",
                {"idempotency_key": uuid4().hex, "reason": "Cross-business attack"},
                f.headers,
                404,
            ),
            ("GET", f.campaign_root + "/" + foreign_campaign["id"], None, f.headers, 404),
            ("PUT", f.campaign_root + "/" + foreign_campaign["id"], f.draft(), f.headers, 404),
            (
                "GET",
                "/api/orders/" + own["id"],
                None,
                {"X-101-Order-Token": other["access_token"]},
                401,
            ),
            (
                "POST",
                f.campaign_root,
                {**f.draft(), "customer_ids": [config["customer_ids"][1]]},
                f.headers,
                404,
            ),
            ("POST", f.campaign_root, f.draft(), {"Cookie": f.headers["Cookie"]}, 403),
            ("GET", f.campaign_root, None, {}, 401),
            (
                "POST",
                f.campaign_root,
                f.draft(),
                {"Cookie": "commerce_staff=invalid", "X-101-CSRF": "invalid"},
                401,
            ),
        ]:
            before = f.snapshot()
            response = f.http.request(
                method, path, headers=headers, **({"json": body} if body else {})
            )
            unchanged = f.snapshot() == before
            result = {
                "method": method,
                "path": path,
                "expected_status": status,
                "status": response.status_code,
                "state_unchanged": unchanged,
                "outcome": "PASS" if response.status_code == status and unchanged else "FAIL",
            }
            results.append(result)
        # Session-changing endpoint excluded from ZAP is exercised independently.
        token = {"X-101-Order-Token": own["access_token"]}
        before_status = f.http.get("/api/orders/" + own["id"], headers=token).status_code
        f.call("POST", "/api/operator/orders/" + own["id"] + "/access/revoke")
        before = f.snapshot()
        revoked_status = f.http.get("/api/orders/" + own["id"], headers=token).status_code
        results.append(
            {
                "name": "revoked_capability",
                "before": before_status,
                "after": revoked_status,
                "outcome": "PASS"
                if before_status == 200 and revoked_status == 401 and before == f.snapshot()
                else "FAIL",
            }
        )
        # A legitimate refund produces one durable effect; its exact replay cannot duplicate it.
        path = f"/api/finance/restaurants/{business}/orders/{own['id']}/refund"
        body = {
            "idempotency_key": "replay-" + uuid4().hex,
            "reason": "Synthetic refund correctness",
        }
        first = f.call("POST", path, body)
        before = f.snapshot()
        second = f.call("POST", path, body)
        results.append(
            {
                "name": "refund_exact_replay",
                "outcome": "PASS"
                if first["id"] == second["id"] and f.snapshot() == before
                else "FAIL",
            }
        )
        provider = f.http.get(config["provider_url"] + "/financial/records").json()
        # Provider's independent ledger must agree; do not infer from HTTP200 alone.
        refunds = [r for r in provider if r["order_id"] == own["id"]]
        results.append(
            {
                "name": "single_provider_refund",
                "count": len(refunds),
                "outcome": "PASS" if len(refunds) == 1 else "FAIL",
            }
        )
    finally:
        f.close()
    result = {
        "execution": "COMPLETE",
        "outcome": "PASS" if results and all(r["outcome"] == "PASS" for r in results) else "FAIL",
        "checks": results,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
