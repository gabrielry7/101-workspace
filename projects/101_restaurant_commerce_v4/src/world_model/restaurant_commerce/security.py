from __future__ import annotations

import hashlib
import hmac
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from secrets import compare_digest
from typing import Callable

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def secure_compare(expected: str, supplied: str | None) -> bool:
    if not supplied:
        return False
    return compare_digest(expected.encode("utf-8"), supplied.encode("utf-8"))


def sign_resource(secret: str, *, kind: str, resource_id: str) -> str:
    msg = f"{kind}:{resource_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_resource_token(secret: str, token: str | None, *, kind: str, resource_id: str) -> bool:
    return secure_compare(sign_resource(secret, kind=kind, resource_id=resource_id), token)


def sign_webhook(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_webhook(secret: str, body: bytes, signature: str | None) -> bool:
    return secure_compare(sign_webhook(secret, body), signature)


class MaxBodySizeMiddleware:
    """Reject oversized bodies before downstream application code sees them.

    Content-Length is used as a cheap fast path. For chunked/unknown-length
    requests we buffer only up to the configured hard limit and replay the body
    to Starlette. This prevents a partial downstream request from starting a DB
    transaction before the limit is discovered.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = 1_048_576) -> None:
        self.app = app
        self.max_bytes = max(1, max_bytes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        length = headers.get("content-length")
        if length:
            try:
                declared = int(length)
            except ValueError:
                await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(scope, receive, send)
                return
            if declared < 0:
                await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(scope, receive, send)
                return
            if declared > self.max_bytes:
                await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
                return

        chunks: list[bytes] = []
        seen = 0
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            seen += len(body)
            if seen > self.max_bytes:
                await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
                return
            chunks.append(body)
            more = bool(message.get("more_body", False))

        payload = b"".join(chunks)
        delivered = False

        async def replay_receive() -> Message:
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": payload, "more_body": False}

        await self.app(scope, replay_receive, send)


class _BodyTooLarge(Exception):
    pass


@dataclass
class _Bucket:
    timestamps: deque[float]
    last_seen: float


class FixedWindowRateLimiter:
    """Bounded, thread-safe per-process limiter for public mutations.

    It is intentionally a second line of defense; production should also apply
    distributed/edge limits. LRU eviction keeps attacker-controlled keys from
    causing unbounded memory or O(n) eviction scans.
    """

    def __init__(self, *, limit: int = 120, window_seconds: int = 60, max_keys: int = 20_000) -> None:
        import threading

        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self.max_keys = max(100, max_keys)
        self._buckets: OrderedDict[str, _Bucket] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                while len(self._buckets) >= self.max_keys:
                    self._buckets.popitem(last=False)
                bucket = _Bucket(deque(), now)
                self._buckets[key] = bucket
            else:
                self._buckets.move_to_end(key)
            bucket.last_seen = now
            while bucket.timestamps and bucket.timestamps[0] <= cutoff:
                bucket.timestamps.popleft()
            if len(bucket.timestamps) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - bucket.timestamps[0])))
                return False, retry_after
            bucket.timestamps.append(now)
            return True, 0

