from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    expires_at: float
    value: T


class TTLCache(Generic[T]):
    """Tiny bounded, thread-safe TTL cache for read-heavy storefront payloads."""

    def __init__(self, *, ttl_seconds: float = 15.0, max_entries: int = 1024) -> None:
        self.ttl_seconds = max(0.0, ttl_seconds)
        self.max_entries = max(1, max_entries)
        self._lock = threading.RLock()
        self._entries: OrderedDict[str, _Entry[T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return entry.value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._entries[key] = _Entry(time.monotonic() + self.ttl_seconds, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def invalidate(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._entries.clear()
            else:
                self._entries.pop(key, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
