"""Wompi sandbox protocol only. Card details never pass through commerce.

The legacy commerce ledger/display uses whole COP pesos despite *_minor names.
This adapter converts pesos to Wompi cents explicitly; no legacy data is changed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx

from .errors import PaymentError
from .payments import PaymentCheckout

API = "https://sandbox.wompi.co/v1"
CHECKOUT_ORIGIN = "https://checkout.wompi.co"
NAME = "wompi_sandbox"
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
STATUS = {"PENDING": "pending", "APPROVED": "paid", "DECLINED": "failed", "ERROR": "failed"}


@dataclass(frozen=True, repr=False)
class SandboxKeys:
    public: str = field(repr=False)
    private: str = field(repr=False)
    events: str = field(repr=False)
    integrity: str = field(repr=False)

    def __post_init__(self):
        for value, prefix in zip(
            (self.public, self.private, self.events, self.integrity),
            ("pub_test_", "prv_test_", "test_events_", "test_integrity_"),
            strict=True,
        ):
            if not isinstance(value, str) or not re.fullmatch(prefix + r"[A-Za-z0-9_-]+", value):
                raise ValueError("All four Wompi sandbox credentials are required")

    @classmethod
    def load(cls, path: Path):
        # Never log this document or an exception containing its values.
        import os
        import stat

        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError("Sandbox credential file must be owned by you with mode 0600")
            body = json.load(stream)
        return cls(
            *(
                body[key]
                for key in (
                    "WOMPI_PUBLIC_KEY",
                    "WOMPI_PRIVATE_KEY",
                    "WOMPI_EVENTS_SECRET",
                    "WOMPI_INTEGRITY_SECRET",
                )
            )
        )


class WompiSandboxProvider:
    name = NAME
    sandbox_only = True
    # Checkout generation is pure: it creates no remote transaction or charge.
    supports_idempotent_checkout = True

    def __init__(
        self,
        keys: SandboxKeys,
        *,
        business_id: str,
        return_url: str,
        transport: httpx.BaseTransport | None = None,
    ):
        parsed = urlsplit(return_url)
        loopback = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            not business_id
            or (parsed.scheme != "https" and not loopback)
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or "\\" in return_url
            or any(ord(c) <= 32 or ord(c) == 127 for c in return_url)
        ):
            raise ValueError("Supply a fixed HTTPS return URL (HTTP allowed only on loopback)")
        _port = parsed.port  # Validate malformed ports.
        self.keys = keys
        self.business_id = business_id
        self.return_url = return_url
        self._transport = transport

    @staticmethod
    def reference(order_id):
        if not IDENTIFIER.fullmatch(order_id):
            raise ValueError("Invalid order identifier")
        return "101sb_" + order_id

    def create_checkout(
        self, *, order_id, public_code, amount_minor, currency, customer_email, idempotency_key=""
    ):
        if currency != "COP" or type(amount_minor) is not int or not 0 < amount_minor <= 20_000_000:
            raise PaymentError("Sandbox checkout requires bounded whole COP pesos")
        reference = self.reference(order_id)
        cents = amount_minor * 100
        signature = hashlib.sha256(
            f"{reference}{cents}COP{self.keys.integrity}".encode()
        ).hexdigest()
        # No contact PII or recovery authority is sent in this URL.
        query = urlencode(
            {
                "public-key": self.keys.public,
                "currency": "COP",
                "amount-in-cents": cents,
                "reference": reference,
                "signature:integrity": signature,
                "redirect-url": self.return_url
                + "?"
                + urlencode({"business_id": self.business_id}),
            }
        )
        return PaymentCheckout(
            NAME, reference, amount_minor, currency, "pending", CHECKOUT_ORIGIN + "/p/?" + query
        )

    def _get(self, path, *, listing=False):
        # Fixed origin, no redirects/proxies, no provider error bodies in logs.
        try:
            with httpx.Client(
                transport=self._transport, timeout=10, follow_redirects=False, trust_env=False
            ) as client:
                with client.stream(
                    "GET",
                    API + path,
                    headers={
                        "Authorization": "Bearer " + self.keys.private,
                        "Accept": "application/json",
                    },
                ) as response:
                    if response.status_code != 200:
                        raise PaymentError(
                            f"Sandbox lookup unavailable (HTTP {response.status_code})"
                        )
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 262144:
                            raise PaymentError("Sandbox lookup response exceeded limit")
            body = json.loads(data)
            if not isinstance(body, dict) or not isinstance(
                body.get("data"), list if listing else dict
            ):
                raise PaymentError("Invalid sandbox response envelope")
            if listing and body.get("meta") not in (None, {}):
                raise PaymentError("Unqualified sandbox pagination metadata")
            return body["data"]
        except (httpx.HTTPError, ValueError, UnicodeError, RecursionError):
            raise PaymentError("Sandbox lookup unavailable or invalid") from None

    def merchant(self):
        result = self._get("/merchants/" + self.keys.public)
        if result.get("public_key") != self.keys.public:
            raise PaymentError("Sandbox merchant key mismatch")
        return result

    def transactions_for_order(self, order_id):
        """Listing is untrusted discovery only, never authority for settlement.

        Empty lists do not establish that payment failed. Saturated or changed
        response shapes require review instead of assuming complete history.
        """
        reference = self.reference(order_id)
        rows = self._get("/transactions?" + urlencode({"reference": reference}), listing=True)
        if len(rows) >= 20:
            raise ValueError("Sandbox reference result requires manual review")
        ids = []
        for row in rows:
            if (
                not isinstance(row, dict)
                or row.get("reference") != reference
                or not isinstance(row.get("id"), str)
                or not IDENTIFIER.fullmatch(row["id"])
            ):
                raise ValueError("Sandbox reference result mismatch")
            if row["id"] not in ids:
                ids.append(row["id"])
        return ids

    def transaction(self, transaction_id):
        if not isinstance(transaction_id, str) or not IDENTIFIER.fullmatch(transaction_id):
            raise ValueError("Invalid sandbox transaction identifier")
        data = self._get("/transactions/" + transaction_id)
        if data.get("id") != transaction_id:
            raise ValueError("Sandbox transaction identifier mismatch")
        # Keep just financial evidence, never card/contact/provider error details.
        if not isinstance(data.get("status"), str):
            raise ValueError("Invalid sandbox status")
        merchant = data.get("merchant")
        if not isinstance(merchant, dict) or merchant.get("public_key") != self.keys.public:
            raise ValueError("Sandbox transaction belongs to a different merchant")
        cents = data.get("amount_in_cents")
        reference = data.get("reference")
        if (
            type(cents) is not int
            or cents <= 0
            or cents % 100
            or data.get("currency") != "COP"
            or not isinstance(reference, str)
            or not reference.startswith("101sb_")
            or not IDENTIFIER.fullmatch(reference[6:])
        ):
            raise ValueError("Sandbox evidence does not match the commerce money contract")
        return {
            "id": transaction_id,
            "order_id": reference[6:],
            "reference": reference,
            "amount_minor": cents // 100,
            "currency": "COP",
            "status": "review_required"
            if data.get("refunds")
            else STATUS.get(data.get("status"), "review_required"),
            "refunds_observed": bool(data.get("refunds")),
        }

    def verify_event(self, event):
        """Validate signed ID/status/amount, then independently query the ID.

        Reference/currency/environment may be unsigned in the native envelope;
        none of those supplied fields authorizes settlement.
        """
        try:
            if event["event"] != "transaction.updated" or event["environment"] != "test":
                raise ValueError
            signature = event["signature"]
            fields = signature["properties"]
            required = {"transaction.id", "transaction.status", "transaction.amount_in_cents"}
            if (
                not isinstance(fields, list)
                or not required.issubset(fields)
                or len(fields) != len(set(fields))
                or len(fields) > 12
                or type(event["timestamp"]) is not int
            ):
                raise ValueError
            values = []
            for path in fields:
                if not isinstance(path, str) or len(path) > 100:
                    raise ValueError
                value = event["data"]
                for part in path.split("."):
                    value = value[part]
                if type(value) not in {str, int}:
                    raise ValueError
                values.append(str(value))
            checksum = hashlib.sha256(
                ("".join(values) + str(event["timestamp"]) + self.keys.events).encode()
            ).hexdigest()
            supplied = signature["checksum"]
            if not isinstance(supplied, str) or not hmac.compare_digest(checksum, supplied.lower()):
                raise ValueError
            transaction_id = event["data"]["transaction"]["id"]
            if not isinstance(transaction_id, str) or not IDENTIFIER.fullmatch(transaction_id):
                raise ValueError
            return transaction_id
        except (KeyError, TypeError, ValueError, AttributeError, UnicodeError):
            raise ValueError("Invalid Wompi sandbox event") from None
