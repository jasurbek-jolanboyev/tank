from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict


@dataclass(slots=True)
class Event:
    event: str
    timestamp: int
    sector: str
    track_id: int | None = None
    details: dict | None = None

    def wire(self) -> dict:
        return {"protocolVersion": 1, "type": "event", **asdict(self)}


class EventStore:
    def __init__(self, capacity: int = 500):
        self.events: deque[Event] = deque(maxlen=capacity)

    def add(self, event: Event) -> Event:
        self.events.append(event)
        return event
