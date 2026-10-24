from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Protocol
from uuid import uuid4

from .errors import DeliveryError


@dataclass(frozen=True)
class DeliveryAddress:
    address_line: str
    city: str
    latitude: float
    longitude: float
    instructions: str | None = None


@dataclass(frozen=True)
class DeliveryQuoteResult:
    provider: str
    provider_quote_reference: str
    fee_minor: int
    currency: str
    distance_meters: int | None
    estimated_pickup_at: datetime | None
    estimated_dropoff_at: datetime | None
    expires_at: datetime
    raw_payload: str | None = None


@dataclass(frozen=True)
class DeliveryDispatchResult:
    provider: str
    provider_delivery_reference: str
    status: str
    tracking_url: str | None = None
    courier_name: str | None = None
    courier_phone: str | None = None
    estimated_pickup_at: datetime | None = None
    estimated_dropoff_at: datetime | None = None
    raw_payload: str | None = None


class DeliveryProvider(Protocol):
    name: str

    def quote(
        self,
        *,
        business_id: str,
        origin: DeliveryAddress,
        destination: DeliveryAddress,
        currency: str,
        prep_minutes: int,
    ) -> DeliveryQuoteResult: ...

    def create_delivery(
        self,
        *,
        order_id: str,
        public_code: str,
        origin: DeliveryAddress,
        destination: DeliveryAddress,
        currency: str,
        fee_minor: int,
        provider_quote_reference: str | None,
        prep_minutes: int,
        customer_name: str,
        customer_phone: str,
        idempotency_key: str = "",
    ) -> DeliveryDispatchResult: ...

    def cancel_delivery(self, *, provider_delivery_reference: str) -> str: ...


def haversine_meters(a: DeliveryAddress, b: DeliveryAddress) -> int:
    """Great-circle distance. Good enough for deterministic local pricing tests."""
    earth_m = 6_371_000.0
    lat1, lon1 = radians(a.latitude), radians(a.longitude)
    lat2, lon2 = radians(b.latitude), radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return int(round(2 * earth_m * asin(sqrt(h))))


class SimulatedDeliveryProvider:
    """Deterministic, network-free courier provider used by the V4 demo/tests.

    Pricing is intentionally simple: a base fee plus a per-km component. It is
    NOT intended to model any real courier company's commercial terms.
    """

    name = "simulated_delivery"

    def __init__(
        self,
        *,
        base_fee_minor: int = 6_000,
        per_km_minor: int = 1_800,
        quote_ttl_minutes: int = 15,
    ) -> None:
        self.base_fee_minor = base_fee_minor
        self.per_km_minor = per_km_minor
        self.quote_ttl_minutes = quote_ttl_minutes

    def quote(
        self,
        *,
        business_id: str,
        origin: DeliveryAddress,
        destination: DeliveryAddress,
        currency: str,
        prep_minutes: int,
    ) -> DeliveryQuoteResult:
        now = datetime.now(timezone.utc)
        distance_m = haversine_meters(origin, destination)
        billed_km = max(1, (distance_m + 999) // 1000)
        fee = self.base_fee_minor + billed_km * self.per_km_minor
        pickup = now + timedelta(minutes=max(0, prep_minutes))
        dropoff = pickup + timedelta(minutes=max(10, int(distance_m / 250)))
        ref = f"simquote_{uuid4().hex}"
        return DeliveryQuoteResult(
            provider=self.name,
            provider_quote_reference=ref,
            fee_minor=fee,
            currency=currency,
            distance_meters=distance_m,
            estimated_pickup_at=pickup,
            estimated_dropoff_at=dropoff,
            expires_at=now + timedelta(minutes=self.quote_ttl_minutes),
            raw_payload=None,
        )

    def create_delivery(
        self,
        *,
        order_id: str,
        public_code: str,
        origin: DeliveryAddress,
        destination: DeliveryAddress,
        currency: str,
        fee_minor: int,
        provider_quote_reference: str | None,
        prep_minutes: int,
        customer_name: str,
        customer_phone: str,
        idempotency_key: str = "",
    ) -> DeliveryDispatchResult:
        now = datetime.now(timezone.utc)
        distance_m = haversine_meters(origin, destination)
        pickup = now + timedelta(minutes=max(0, prep_minutes))
        dropoff = pickup + timedelta(minutes=max(10, int(distance_m / 250)))
        ref = f"simdel_{order_id}"
        return DeliveryDispatchResult(
            provider=self.name,
            provider_delivery_reference=ref,
            status="courier_assigned",
            tracking_url=f"/demo/delivery/{ref}",
            courier_name="Courier 101",
            courier_phone="+570000000000",
            estimated_pickup_at=pickup,
            estimated_dropoff_at=dropoff,
            raw_payload=None,
        )

    def cancel_delivery(self, *, provider_delivery_reference: str) -> str:
        return "cancelled"


class UberDirectDeliveryProvider:
    """Production boundary only. V4 performs no live Uber Direct calls."""

    name = "uber_direct"

    def __init__(self, *, configured: bool = False) -> None:
        self.configured = configured

    def quote(self, **_: object) -> DeliveryQuoteResult:
        raise DeliveryError(
            "Uber Direct is a production integration boundary in V4; live calls are not configured."
        )

    def create_delivery(self, **_: object) -> DeliveryDispatchResult:
        raise DeliveryError(
            "Uber Direct is a production integration boundary in V4; live calls are not configured."
        )

    def cancel_delivery(self, *, provider_delivery_reference: str) -> str:
        raise DeliveryError(
            "Uber Direct is a production integration boundary in V4; live calls are not configured."
        )


class MensajerosUrbanosDeliveryProvider:
    """Production boundary only. V4 performs no live Mensajeros Urbanos calls."""

    name = "mensajeros_urbanos"

    def __init__(self, *, configured: bool = False) -> None:
        self.configured = configured

    def quote(self, **_: object) -> DeliveryQuoteResult:
        raise DeliveryError(
            "Mensajeros Urbanos is a production integration boundary in V4; live calls are not configured."
        )

    def create_delivery(self, **_: object) -> DeliveryDispatchResult:
        raise DeliveryError(
            "Mensajeros Urbanos is a production integration boundary in V4; live calls are not configured."
        )

    def cancel_delivery(self, *, provider_delivery_reference: str) -> str:
        raise DeliveryError(
            "Mensajeros Urbanos is a production integration boundary in V4; live calls are not configured."
        )
