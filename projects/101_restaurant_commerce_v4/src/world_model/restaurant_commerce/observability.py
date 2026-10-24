from __future__ import annotations

import threading
import time
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class MetricsRegistry:
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    requests_total: Counter = field(default_factory=Counter)
    errors_total: Counter = field(default_factory=Counter)
    latency_ms_total: Counter = field(default_factory=Counter)
    latency_count: Counter = field(default_factory=Counter)

    def record_request(self, method: str, route: str, status: int, elapsed_ms: float) -> None:
        route = route or "unmatched"
        key = f"{method} {route}"
        with self._lock:
            self.requests_total[(key, status)] += 1
            self.latency_ms_total[key] += elapsed_ms
            self.latency_count[key] += 1
            if status >= 500:
                self.errors_total[key] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            requests = {
                f"{key}|{status}": count
                for (key, status), count in sorted(self.requests_total.items())
            }
            latency = {
                key: round(self.latency_ms_total[key] / self.latency_count[key], 3)
                for key in sorted(self.latency_count)
                if self.latency_count[key]
            }
            return {
                "requests_total": requests,
                "server_errors_total": dict(self.errors_total),
                "average_latency_ms": latency,
            }
