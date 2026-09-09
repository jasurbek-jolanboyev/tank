from __future__ import annotations

from app.models import IndicatorState, RangeMeasurement, Track
from app.ranging.filter import DistanceFilter


class SensorFusionEngine:
    def __init__(self, policy: dict):
        self.policy = policy
        self.ranges: dict[str, RangeMeasurement] = {}
        self.filters: dict[str, DistanceFilter] = {}
        self.near: dict[str, bool] = {}
        self.near_enter_samples: dict[str, int] = {}
        self.near_exit_samples: dict[str, int] = {}

    def observe_range(self, measurement: RangeMeasurement) -> None:
        if measurement.valid and measurement.distance_meters is not None:
            value = self.filters.setdefault(
                measurement.sector,
                DistanceFilter(
                    window=int(self.policy.get("distanceFilterWindow", 1)),
                    alpha=float(self.policy.get("distanceFilterAlpha", 1.0)),
                    outlier_m=float(self.policy.get("distanceOutlierMeters", 15.0)),
                ),
            ).update(measurement.distance_meters)
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
        enter_samples = max(1, int(self.policy.get("nearEnterSamples", 1)))
        exit_samples = max(1, int(self.policy.get("nearExitSamples", 1)))
        if track.distance_meters is not None:
            if not is_near and track.distance_meters <= self.policy["nearEnterMeters"]:
                self.near_enter_samples[track.sector] = self.near_enter_samples.get(track.sector, 0) + 1
                self.near_exit_samples[track.sector] = 0
                if self.near_enter_samples[track.sector] >= enter_samples:
                    is_near = True
                    self.near_enter_samples[track.sector] = 0
            elif is_near and track.distance_meters >= self.policy["nearExitMeters"]:
                self.near_exit_samples[track.sector] = self.near_exit_samples.get(track.sector, 0) + 1
                self.near_enter_samples[track.sector] = 0
                if self.near_exit_samples[track.sector] >= exit_samples:
                    is_near = False
                    self.near_exit_samples[track.sector] = 0
            else:
                self.near_enter_samples[track.sector] = 0
                self.near_exit_samples[track.sector] = 0
        else:
            is_near = False
            self.near_enter_samples[track.sector] = 0
            self.near_exit_samples[track.sector] = 0
        self.near[track.sector] = is_near
        red = is_near and (not self.policy["requireApproachingForRed"] or track.approaching)
        track.indicator = IndicatorState.RED if red else IndicatorState.WHITE
        return track
