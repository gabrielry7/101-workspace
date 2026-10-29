import json
import os
import time
import uuid
from pathlib import Path

from locust import HttpUser, between, events, task

c = json.loads(Path(os.environ["COMMERCE_TEST_CONFIG"]).read_text())
profile = os.environ["COMMERCE_LOAD_PROFILE"]
completed = set()
peak = 0
start = time.time()
root = "/api/restaurants/" + c["business_ids"][0]


@events.spawning_complete.add_listener
def spawned(user_count, **kw):
    global peak
    peak = max(peak, user_count)


@events.quitting.add_listener
def finish(environment, **kw):
    Path(os.environ["COMMERCE_LOAD_RECEIPT"]).write_text(
        json.dumps(
            {
                "peak_users": peak,
                "completed_checkouts": len(completed),
                "duration_seconds": time.time() - start,
                "unique_orders": sorted(completed),
                "total_requests": environment.stats.total.num_requests,
                "failures": environment.stats.total.num_failures,
                "operations": [
                    {
                        "method": s.method,
                        "name": s.name,
                        "requests": s.num_requests,
                        "failures": s.num_failures,
                        "mean_ms": s.avg_response_time,
                        "p95_ms": s.get_response_time_percentile(0.95),
                        "p99_ms": s.get_response_time_percentile(0.99),
                    }
                    for s in environment.stats.entries.values()
                ],
            },
            indent=2,
        )
    )


class Customer(HttpUser):
    wait_time = between(0.2, 0.5)

    @task(3)
    def browse(self):
        self.client.get(root + "/storefront", name="storefront")

    @task(2)
    def quote(self):
        self.client.post(
            root + "/orders/quote", json={"items": c["cart"]}, name="quote"
        )

    @task
    def checkout(self):
        key = "load-" + profile + "-" + uuid.uuid4().hex
        body = {
            "customer": {"name": "Load synthetic", "phone": "3005550200"},
            "items": c["cart"],
            "idempotency_key": key,
        }
        with self.client.post(
            root + "/orders", json=body, name="checkout", catch_response=True
        ) as response:
            if response.status_code != 200:
                return
            try:
                order = response.json()
                oid = order["id"]
                token = order["access_token"]
            except (ValueError, KeyError, TypeError):
                response.failure("invalid order response")
                return
        with self.client.post(
            root + "/orders",
            json=body,
            name="checkout-exact-replay",
            catch_response=True,
        ) as response:
            if response.status_code != 200 or response.json().get("id") != oid:
                response.failure("replay mismatch")
                return
        # A recovery worker can own the same intent before the request handler.
        # Pending is a successful durable acceptance, not payment readiness.
        deadline = time.monotonic() + 10
        while not order.get("payments"):
            with self.client.get(
                "/api/orders/" + oid,
                headers={"X-101-Order-Token": token},
                name="checkout-pending-status",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    return
                order = response.json()
                if order.get("id") != oid or order.get("reconciliation_required"):
                    response.failure("pending checkout identity/reconciliation failure")
                    return
                if not order.get("payments") and time.monotonic() >= deadline:
                    response.failure("pending checkout did not become ready within10s")
                    return
            if not order.get("payments"):
                time.sleep(0.1)
        with self.client.post(
            "/api/payments/simulated/"
            + order["payments"][0]["provider_reference"]
            + "/complete",
            name="payment-complete",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                return
        with self.client.get(
            "/api/orders/" + oid,
            headers={"X-101-Order-Token": token},
            name="order-status",
            catch_response=True,
        ) as response:
            if (
                response.status_code != 200
                or response.json().get("payment_status") != "paid"
            ):
                response.failure("payment status mismatch")
                return
        completed.add(oid)
