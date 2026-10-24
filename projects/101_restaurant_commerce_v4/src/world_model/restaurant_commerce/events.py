from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CommerceEvent:
    kind: str
    business_id: str
    entity_id: str
    occurred_at: datetime
    payload: dict[str, object]
    event_id: str | None = None
    dedupe_key: str | None = None


class EventSink(Protocol):
    def publish(self, event: CommerceEvent) -> None: ...


class NullEventSink:
    def publish(self, event: CommerceEvent) -> None:
        return None


class MemoryEventSink:
    def __init__(self) -> None:
        self.events: list[CommerceEvent] = []

    def publish(self, event: CommerceEvent) -> None:
        self.events.append(event)
