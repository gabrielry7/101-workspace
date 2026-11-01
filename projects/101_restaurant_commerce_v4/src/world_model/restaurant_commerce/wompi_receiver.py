"""Optional sandbox inbox consumer. Commit local receipt before remote ack."""

import json
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .errors import PaymentError
from .wompi_sandbox import NAME


class SandboxReceiver:
    def __init__(self, url, token, *, transport=None):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
            or parsed.port not in (None, 443)
            or "\\" in url
            or any(ord(c) <= 32 for c in url)
            or not re.fullmatch(r"[a-f0-9]{64}", token)
        ):
            raise ValueError("Invalid sandbox receiver configuration")
        self.url, self._token, self._transport = url.rstrip("/"), token, transport

    @classmethod
    def load(cls, path: Path):
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as f:
            info = os.fstat(f.fileno())
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError("Receiver configuration must be private mode 0600")
            data = json.load(f)
        return cls(data["url"], data["token"])

    def request(self, method, path, body=None):
        try:
            with httpx.Client(
                transport=self._transport, timeout=10, follow_redirects=False, trust_env=False
            ) as client:
                with client.stream(
                    method,
                    self.url + path,
                    json=body,
                    headers={"Authorization": "Bearer " + self._token},
                ) as response:
                    if response.status_code != 200:
                        raise PaymentError("Sandbox receiver unavailable")
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 262144:
                            raise PaymentError("Sandbox receiver exceeded response limit")
            return json.loads(data)
        except (httpx.HTTPError, ValueError, UnicodeError, RecursionError):
            raise PaymentError("Sandbox receiver unavailable or invalid") from None

    def drain(self, service):
        from .wompi_workflow import enqueue

        adapter = service.payment_providers[NAME]
        body = self.request("GET", "/private/events")
        rows = body.get("events") if isinstance(body, dict) else None
        if not isinstance(rows, list) or len(rows) > 20:
            raise PaymentError("Invalid sandbox receiver envelope")
        ack = []
        for row in rows:
            try:
                event = row["event"]
                transaction_id = adapter.verify_event(event)
                checksum = event["signature"]["checksum"].lower()
                if row["id"] != checksum:
                    raise ValueError("Receipt key mismatch")
            except (ValueError, TypeError, KeyError):
                continue  # Other valid receipts must still progress.
            enqueue(service, transaction_id, event_key=checksum)
            ack.append(checksum)
        if ack:
            self.request("POST", "/private/ack", {"ids": ack})
        return len(ack)
