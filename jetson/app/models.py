from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class ObjectClass(StrEnum):
    DRONE = "drone"
    BIRD = "bird"
    AIRCRAFT = "aircraft"
    PERSON = "person"
    UNKNOWN_AIR_OBJECT = "unknown_air_object"


class IndicatorState(StrEnum):
    OFF = "OFF"
    WHITE = "WHITE"
    RED = "RED"


SECTORS = (
    "TOP_1", "TOP_2", "TOP_3", "FRONT_1", "FRONT_2", "REAR_1",
    "REAR_2", "LEFT_1", "LEFT_2", "RIGHT_1", "RIGHT_2",
)


@dataclass(slots=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def valid(self) -> bool:
        return (0 <= self.x <= 1 and 0 <= self.y <= 1 and self.width > 0
                and self.height > 0 and self.x + self.width <= 1
                and self.y + self.height <= 1)


@dataclass(slots=True)
class Detection:
    detection_id: str
    camera_id: str
    sector: str
    object_class: ObjectClass
    confidence: float
    bbox: BoundingBox
    timestamp_ms: int
    source: str
    simulated: bool = False


@dataclass(slots=True)
class RangeMeasurement:
    node_id: str
    sector: str
    distance_meters: float | None
    timestamp_ms: int
    valid: bool
    sensor_id: str | None = None
    signal_strength: int | None = None
    temperature_c: float | None = None


@dataclass(slots=True)
class Track:
    track_id: int
    camera_id: str
    sector: str
    object_class: ObjectClass
    confidence: float
    bbox: BoundingBox
    first_seen_ms: int
    last_seen_ms: int
    consecutive: int = 1
    confirmed: bool = False
    approaching: bool = False
    distance_meters: float | None = None
    indicator: IndicatorState = IndicatorState.OFF
    confidence_history: list[float] = field(default_factory=list)
    bbox_history: list[BoundingBox] = field(default_factory=list)
    range_history: list[float] = field(default_factory=list)

    def wire(self) -> dict[str, Any]:
        result = asdict(self)
        result["object_class"] = self.object_class.value
        result["indicator"] = self.indicator.value
        return result
