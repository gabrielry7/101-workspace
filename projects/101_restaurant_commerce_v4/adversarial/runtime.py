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


class ControlledFinancial:
    name = "simulated"
    controlled = True
    refund_enabled = True
    supports_idempotent_refund = True

    def _call(self, route, kwargs, model):
        response = httpx.post(
            config()["provider_url"] + "/financial/" + route,
            json=kwargs,
            timeout=4,
            trust_env=False,
        )
        response.raise_for_status()
        body = response.json()
        return model(**body) if body is not None else None

    def lookup_payment(self, **kwargs):
        from world_model.restaurant_commerce.financial_providers import PaymentObservation

        return self._call("lookup-payment", kwargs, PaymentObservation)

    def lookup_refund(self, **kwargs):
        from world_model.restaurant_commerce.financial_providers import RefundObservation

        return self._call("lookup-refund", kwargs, RefundObservation)

    def refund(self, **kwargs):
        from world_model.restaurant_commerce.financial_providers import RefundObservation

        return self._call("refund", kwargs, RefundObservation)


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
        payment_recovery_enabled=False,
        provider_recovery_enabled=False,
        payment_providers={"simulated": ControlledPayment()},
        financial_providers={"simulated": ControlledFinancial()},
        delivery_providers={"simulated_delivery": ControlledDelivery()},
        event_sink=ControlledEvents(),
        rate_limit_per_minute=c.get("rate_limit_per_minute", 100000),
        payment_lease_seconds=c.get("payment_lease_seconds", 5),
    )
    # Harness proof only: no additional application authority or login endpoints.
    if c.get("timing_enabled"):
        from timing import install
        return install(app, str(Path(c["run_dir"]) / "timing"))
    return app


def recover():
    """Run the installed recovery implementation in an independently owned process."""
    import signal

    from world_model.restaurant_commerce.db import make_engine, session_factory
    from world_model.restaurant_commerce.recovery import start_recovery

    c = config()
    engine = make_engine(c["database_url"])
    stop, thread = start_recovery(
        session_factory(engine),
        interval_seconds=1,
        service_options={
            "payment_providers": {"simulated": ControlledPayment()},
            "financial_providers": {"simulated": ControlledFinancial()},
            "delivery_providers": {"simulated_delivery": ControlledDelivery()},
            "event_sink": ControlledEvents(),
            "payment_lease_seconds": c.get("payment_lease_seconds", 5),
        },
    )

    def halt(*_):
        stop.set()

    signal.signal(signal.SIGTERM, halt)
    signal.signal(signal.SIGINT, halt)
    while not stop.wait(0.2):
        if not thread.is_alive():
            raise RuntimeError("Recovery thread exited unexpectedly")
    thread.join(timeout=5)
    engine.dispose()


if __name__ == "__main__":
    recover()
