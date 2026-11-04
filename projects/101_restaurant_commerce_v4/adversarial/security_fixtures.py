"""Real disposable records shared by S01 scanner seeds and S02 fuzz setup.

No production configuration or provider credentials are read. Financial effects
are performed only by the loopback controlled provider. Do not publish returned
capabilities or the generated private configuration.
"""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session
from world_model.restaurant_commerce.campaign_models import CampaignSettings
from world_model.restaurant_commerce.models import (
    Base,
    Customer,
    OutboundMessage,
    PaymentReconciliation,
)


class Fixtures:
    def __init__(self, config):
        for url in (
            config["base_url"],
            config["database_url"],
            config.get("provider_url", config["base_url"]),
        ):
            if urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Disposable loopback fixtures only")
        self.config = config
        self.business = config["business_ids"][0]
        self.headers = config["single_staff_headers"]
        self.http = httpx.Client(base_url=config["base_url"], trust_env=False, timeout=15)
        self.engine = create_engine(config["database_url"])
        self.installed_tables = set(inspect(self.engine).get_table_names())
        self.campaign_root = f"/api/operator/restaurants/{self.business}/campaigns"
        with Session(self.engine) as session:
            for i, business in enumerate(config["business_ids"]):
                if not session.get(CampaignSettings, business):
                    session.add(
                        CampaignSettings(
                            business_id=business,
                            scope="test",
                            config_json=json.dumps(
                                {
                                    "sender": "synthetic@example.test",
                                    "brand": {"name": "Synthetic business"},
                                    "frequency_hours": 24,
                                }
                            ),
                        )
                    )
                customer = session.get(Customer, config["customer_ids"][i])
                customer.email = f"coverage-{i}@example.test"
                customer.whatsapp_opt_in = customer.marketing_opt_in = True
                customer.whatsapp_verified_at = customer.marketing_verified_at = datetime.now(UTC)
            session.commit()
        store = self.call("GET", f"/api/restaurants/{self.business}/storefront")
        item = next(
            i
            for m in store["menus"]
            for cat in m["categories"]
            for i in cat["items"]
            if i["available"] and not i["modifier_groups"]
        )
        self.cart = [{"menu_item_id": item["id"], "quantity": 1, "modifiers": []}]

    def close(self):
        self.http.close()
        self.engine.dispose()

    def call(self, method, path, body=None, *, headers=None):
        kw = {"headers": self.headers if headers is None else headers}
        if body is not None:
            kw["json"] = body
        response = self.http.request(method, path, **kw)
        if response.status_code != 200:
            # Do not expose response capabilities or request credentials.
            raise AssertionError(
                f"Fixture setup {method} {path}: HTTP{response.status_code}: {response.text[:500]}"
            )
        return response.json()

    def draft(self):
        now = datetime.now(UTC)
        return {
            "sender": "synthetic@example.test",
            "content": {
                "subject": "Synthetic invitation",
                "title": "Synthetic title",
                "body": "Disposable scan content",
                "terms": "No real offer",
            },
            "customer_ids": [self.config["customer_ids"][0]],
            "scheduled_at": (now + timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
            "scope": "test",
            "budget_microusd": 0,
        }

    def order(self, *, delivery=False):
        body = {
            "customer": {"name": "Synthetic security", "phone": "3005550123"},
            "items": self.cart,
            "idempotency_key": "coverage-" + uuid4().hex,
        }
        if delivery:
            quote = self.call(
                "POST",
                f"/api/restaurants/{self.business}/delivery/quote",
                {
                    "destination": {
                        "address_line": "Synthetic street",
                        "city": "Bogotá",
                        "latitude": 4.6697,
                        "longitude": -74.0549,
                    }
                },
            )
            body.update(fulfillment_type="delivery", delivery_quote_id=quote["id"])
        return self.call("POST", f"/api/restaurants/{self.business}/orders", body)

    def prepare(self, method, path):
        """Fresh operation-specific records; generated body mutations remain untouched."""
        ids = {"business_id": self.business, "customer_id": self.config["customer_ids"][0]}
        body = None
        if "/campaigns" in path:
            draft = self.draft()
            # Each case gets its own draft, avoiding prior approval/cancellation state.
            campaign = self.call("POST", self.campaign_root, draft)
            ids["campaign_id"] = campaign["id"]
            if path.endswith("/approve") or path.endswith("/schedule"):
                body = {"digest": campaign["digest"]}
                if path.endswith("/schedule"):
                    self.call("POST", self.campaign_root + "/" + campaign["id"] + "/approve", body)
            elif path.endswith("/pause"):
                body = {"paused": False}
            elif method in {"POST", "PUT"} and path.endswith(("/campaigns", "/{campaign_id}")):
                body = draft
        elif "/finance/" in path:
            self.http.post(
                self.config["provider_url"] + "/control", json={"mode": "paid"}
            ).raise_for_status()
            order = self.order()
            ids["order_id"] = order["id"]
            body = {
                "idempotency_key": "finance-" + uuid4().hex,
                "reason": "Synthetic security verification",
            }
            if "{reconciliation_id}" in path:
                # Existing domain record, with real lookup evidence newer than the review.
                with Session(self.engine) as session:
                    row = PaymentReconciliation(
                        order_id=order["id"],
                        business_id=self.business,
                        reason="synthetic_review",
                        evidence_json="{}",
                    )
                    session.add(row)
                    session.commit()
                    ids["reconciliation_id"] = row.id
                op = self.call(
                    "POST",
                    f"/api/finance/restaurants/{self.business}/orders/{order['id']}/lookup",
                    body,
                )
                body = {"operation_id": op["id"], "reason": "Synthetic evidence resolution"}
        elif "{delivery_id}" in path:
            self.http.post(
                self.config["provider_url"] + "/control", json={"mode": "paid"}
            ).raise_for_status()
            order = self.order(delivery=True)
            self.call("PATCH", f"/api/operator/orders/{order['id']}", {"status": "accepted"})
            delivery = self.call("POST", f"/api/operator/orders/{order['id']}/delivery/dispatch")
            ids.update(order_id=order["id"], delivery_id=delivery["id"])
            for status in ["preparing", "ready"]:
                self.call("PATCH", f"/api/operator/orders/{order['id']}", {"status": status})
            body = {"status": "picked_up"}
        elif "{message_id}" in path:
            with Session(self.engine) as session:
                customer = session.get(Customer, ids["customer_id"])
                row = OutboundMessage(
                    business_id=self.business,
                    customer_id=customer.id,
                    purpose="marketing",
                    message_kind="synthetic",
                    destination=customer.phone,
                    body="Synthetic handoff",
                    scheduled_at=datetime.now(UTC),
                    dedupe_key=uuid4().hex,
                )
                session.add(row)
                session.commit()
                ids["message_id"] = row.id
            if path.endswith("/sent"):
                body = {}
        return ids, body

    def snapshot(self):
        """Stable financial/campaign evidence; exclude worker leases and access logs."""
        names = [
            "restaurant_orders",
            "restaurant_payments",
            "restaurant_financial_operations",
            "restaurant_payment_reconciliations",
            "restaurant_loyalty_ledger",
            "restaurant_campaigns",
            "restaurant_campaign_revisions",
            "restaurant_campaign_approvals",
            "restaurant_campaign_settings",
            "restaurant_outbound_messages",
            "restaurant_customers",
            "restaurant_deliveries",
            "restaurant_delivery_events",
            "restaurant_payment_intents",
            "restaurant_idempotency_records",
            "restaurant_loyalty_accounts",
            "restaurant_campaign_jobs",
            "restaurant_campaign_attempts",
            "restaurant_campaign_events",
            "restaurant_contact_permissions",
            "restaurant_permission_evidence",
        ]
        # Stage3 legacy-wallet/refund consumers can write these tables even when
        # experiment selection is disabled. Include them in rejection invariants.
        names = sorted(
            set(names)
            | {
                n
                for n in Base.metadata.tables
                if n.startswith("restaurant_loyalty_") and n in self.installed_tables
            }
        )
        self.invariant_tables = names
        result = {}
        with self.engine.connect() as conn:
            for name in names:
                assert name in Base.metadata.tables, f"Missing invariant table: {name}"
                if name in Base.metadata.tables:
                    result[name] = sorted(
                        (
                            dict(r)
                            for r in conn.execute(select(Base.metadata.tables[name])).mappings()
                        ),
                        key=lambda r: str(r.get("id", "")),
                    )
        return json.dumps(result, sort_keys=True, default=str)
