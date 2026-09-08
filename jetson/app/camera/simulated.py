from __future__ import annotations

import asyncio
import time

from app.camera.base import CameraFrame


class SimulatedCamera:
    def __init__(self, camera_id: str, sector: str, fps: float = 10):
        self.camera_id, self.sector = camera_id, sector
        self.period = 1 / max(fps, 0.1)
        self.sequence = 0
        self.closed = False

    async def read(self) -> CameraFrame | None:
        if self.closed:
            return None
        await asyncio.sleep(self.period)
        self.sequence += 1
        return CameraFrame(self.camera_id, self.sector, self.sequence,
                           int(time.monotonic() * 1000), simulated=True)

    async def close(self) -> None:
        self.closed = True
