from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class CameraFrame:
    camera_id: str
    sector: str
    sequence: int
    timestamp_ms: int
    image: Any = None
    simulated: bool = False


class ICameraSource(Protocol):
    async def read(self) -> CameraFrame | None: ...
    async def close(self) -> None: ...


class LatestFrameQueue:
    """Bounded latest-frame queue; stale frames are intentionally discarded."""

    def __init__(self, capacity: int = 1):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._queue: asyncio.Queue[CameraFrame] = asyncio.Queue(capacity)
        self.dropped = 0

    def put_latest(self, frame: CameraFrame) -> None:
        while self._queue.full():
            self._queue.get_nowait()
            self.dropped += 1
        self._queue.put_nowait(frame)

    async def get(self) -> CameraFrame:
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()
