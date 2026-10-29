"""Disposable harness adapters; imports the installed commerce wheel, not source."""

import json
import os
from dataclasses import asdict
from pathlib import Path

import httpx

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.deliveries import SimulatedDeliveryProvider
from world_model.restaurant_commerce.payments import PaymentCheckout


def config():
    return json.loads(Path(os.environ["COMMERCE_TEST_CONFIG"]).read_text())


class ControlledPayment:
    name = "simulated"
    supports_idempotent_checkout = True

    def create_checkout(self, **kwargs):
        c = config()
        response = httpx.post(
            c["provider_url"] + "/checkouts", json=kwargs, timeout=4, trust_env=False
        )
        response.raise_for_status()
        return PaymentCheckout(**response.json())


class ControlledDelivery(SimulatedDeliveryProvider):
    def quote(self, **kwargs):
        self._record("quote", kwargs)
        return super().quote(**kwargs)

    def create_delivery(self, **kwargs):
        self._record("dispatch", kwargs)
        return super().create_delivery(**kwargs)

    def cancel_delivery(self, **kwargs):
        self._record("cancel", kwargs)
        return super().cancel_delivery(**kwargs)

    def _record(self, kind, kwargs):
        c = config()
        httpx.post(
            c["provider_url"] + "/delivery/" + kind,
            json=json.loads(json.dumps(kwargs, default=str)),
            timeout=4,
            trust_env=False,
        ).raise_for_status()


class ControlledEvents:
    def publish(self, event):
        httpx.post(
            config()["provider_url"] + "/events",
            json=json.loads(json.dumps(asdict(event), default=str)),
            timeout=4,
            trust_env=False,
        ).raise_for_status()


def application():
    c = config()
    app = create_app(
        database_url=c["database_url"],
        operator_token=c["operator_token"],
        public_access_secret=c["access_secret"],
        webhook_secrets=c["webhook_secrets"],
        environment="development",
        demo_mode=True,
        auto_init_schema=False,
        payment_providers={"simulated": ControlledPayment()},
        delivery_providers={"simulated_delivery": ControlledDelivery()},
        event_sink=ControlledEvents(),
        rate_limit_per_minute=c.get("rate_limit_per_minute", 100000),
        payment_lease_seconds=c.get("payment_lease_seconds", 5),
    )
    # Harness proof only: no additional application authority or login endpoints.
    return app
