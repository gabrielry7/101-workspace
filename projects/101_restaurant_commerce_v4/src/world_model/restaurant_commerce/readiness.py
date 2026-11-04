"""Bound HTTP probes without spawning work for every health-check request.

Use the actual application pool: exhaustion and its configured search_path must
be observed. A network/pool stall may outlive the HTTP deadline; at most one
probe thread per process can remain occupied. Never cache a successful result.
"""

from __future__ import annotations

import asyncio
import math
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future


class ReadinessProbe:
    def __init__(self, check: Callable[[float], bool], *, timeout: float = 1.0):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Readiness timeout must be finite and positive")
        self.check = check
        self.timeout = timeout
        self._lock = threading.Lock()
        self._flight: tuple[Future, float] | None = None
        self._closed = False

    async def ready(self) -> bool:
        with self._lock:
            if self._closed:
                return False
            if self._flight is None or self._flight[0].done():
                future: Future = Future()
                deadline = time.monotonic() + self.timeout
                self._flight = future, deadline
                threading.Thread(
                    target=self._run,
                    args=(future, deadline),
                    name="commerce-readiness",
                    daemon=True,
                ).start()
            future, deadline = self._flight
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            result = await asyncio.wait_for(
                asyncio.shield(asyncio.wrap_future(future)), timeout=remaining
            )
            return bool(result) and time.monotonic() <= deadline
        except TimeoutError:
            return False

    def _run(self, future: Future, deadline: float) -> None:
        try:
            result = self.check(deadline)
        except Exception:
            # Probe errors fail closed; never disclose DB/schema details publicly.
            result = False
        future.set_result(bool(result) and time.monotonic() <= deadline)

    def close(self) -> None:
        # Never wait on an uncancellable DB driver call during ASGI shutdown.
        with self._lock:
            self._closed = True
