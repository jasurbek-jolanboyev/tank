from __future__ import annotations

from app.models import IndicatorState, RangeMeasurement, Track
from app.ranging.filter import DistanceFilter


class SensorFusionEngine:
    def __init__(self, policy: dict):
        self.policy = policy
        self.ranges: dict[str, RangeMeasurement] = {}
        self.filters: dict[str, DistanceFilter] = {}
        self.near: dict[str, bool] = {}

    def observe_range(self, measurement: RangeMeasurement) -> None:
        if measurement.valid and measurement.distance_meters is not None:
            value = self.filters.setdefault(measurement.sector, DistanceFilter()).update(measurement.distance_meters)
            measurement.distance_meters = value
        self.ranges[measurement.sector] = measurement

    def fuse(self, track: Track, now_ms: int) -> Track:
        measurement = self.ranges.get(track.sector)
        if (measurement and measurement.valid and measurement.distance_meters is not None
                and now_ms - measurement.timestamp_ms <= self.policy["maximumRangeAgeMs"]):
            previous = track.distance_meters
            track.distance_meters = measurement.distance_meters
            if previous is not None:
                track.approaching = track.distance_meters < previous - 0.1
            track.range_history = (track.range_history + [track.distance_meters])[-16:]
        if not track.confirmed:
            track.indicator = IndicatorState.OFF
            self.near[track.sector] = False
            return track
        is_near = self.near.get(track.sector, False)
        if track.distance_meters is not None:
            if not is_near and track.distance_meters <= self.policy["nearEnterMeters"]:
                is_near = True
            elif is_near and track.distance_meters >= self.policy["nearExitMeters"]:
                is_near = False
        else:
            is_near = False
        self.near[track.sector] = is_near
        red = is_near and (not self.policy["requireApproachingForRed"] or track.approaching)
        track.indicator = IndicatorState.RED if red else IndicatorState.WHITE
        return track
