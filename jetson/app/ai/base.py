from __future__ import annotations

from typing import Protocol

from app.camera.base import CameraFrame
from app.models import Detection


class IObjectDetector(Protocol):
    name: str
    async def detect(self, frame: CameraFrame) -> list[Detection]: ...
