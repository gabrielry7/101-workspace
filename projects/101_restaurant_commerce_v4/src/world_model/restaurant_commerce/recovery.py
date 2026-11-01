"""Small in-process recovery runner; DB leases coordinate every API worker."""

import logging
from threading import Event, Thread

from .service import RestaurantCommerceService

logger = logging.getLogger("101.restaurant_commerce.recovery")


def start_recovery(session_factory, *, interval_seconds, service_options):
    stop = Event()

    def run():
        while not stop.wait(interval_seconds):
            try:
                with session_factory() as session:
                    service = RestaurantCommerceService(session, **service_options)
                    service.recover_payments(limit=25)
                    service.recover_financial_operations(limit=25)
                    service.drain_event_outbox(limit=25)
                    from .wompi_workflow import recover
                    recover(service, limit=5)
            except Exception as exc:  # noqa: BLE001 - next cycle retries; no exception text/PII in log
                logger.warning("Payment recovery deferred (%s)", type(exc).__name__)

    thread = Thread(target=run, name="commerce-payment-recovery", daemon=True)
    thread.start()
    return stop, thread
