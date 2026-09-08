from __future__ import annotations

from app.camera.base import CameraFrame
from app.models import BoundingBox, Detection, ObjectClass


class MockDetector:
    name = "mock-detector"

    async def detect(self, frame: CameraFrame) -> list[Detection]:
        # Repeatable scenario: candidate appears, approaches, then disappears.
        phase = frame.sequence % 50
        if phase >= 35:
            return []
        object_class = ObjectClass.BIRD if 25 <= phase < 28 else ObjectClass.DRONE
        confidence = 0.88 if object_class is ObjectClass.DRONE else 0.83
        size = 0.10 + min(phase, 24) * 0.003
        return [Detection(f"{frame.camera_id}-{frame.sequence}", frame.camera_id,
                          frame.sector, object_class, confidence,
                          BoundingBox(0.45, 0.35, size, size * 0.75),
                          frame.timestamp_ms, self.name, simulated=True)]
