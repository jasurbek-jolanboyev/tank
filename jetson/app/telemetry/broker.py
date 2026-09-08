from __future__ import annotations

import asyncio


class TelemetryBroker:
    def __init__(self):
        self.subscribers: set[asyncio.Queue[dict]] = set()

    def subscribe(self) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(128)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict]) -> None:
        self.subscribers.discard(queue)

    def publish(self, message: dict) -> None:
        for queue in tuple(self.subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(message)
