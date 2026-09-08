from __future__ import annotations

from app.models import BoundingBox, Detection, Track


def _iou(a: BoundingBox, b: BoundingBox) -> float:
    left, top = max(a.x, b.x), max(a.y, b.y)
    right = min(a.x + a.width, b.x + b.width)
    bottom = min(a.y + a.height, b.y + b.height)
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = a.width * a.height + b.width * b.height - intersection
    return intersection / union if union else 0.0


class TrackManager:
    def __init__(self, policy: dict):
        self.policy = policy
        self.tracks: dict[int, Track] = {}
        self.next_id = 1
        self.last_expired: list[Track] = []

    def update(self, detections: list[Detection], now_ms: int) -> list[Track]:
        updated: list[Track] = []
        for detection in detections:
            if not detection.bbox.valid() or not 0 <= detection.confidence <= 1:
                continue
            candidates = [t for t in self.tracks.values()
                          if t.camera_id == detection.camera_id
                          and t.object_class == detection.object_class
                          and now_ms - t.last_seen_ms <= self.policy["maximumGapMs"]]
            track = max(candidates, key=lambda t: _iou(t.bbox, detection.bbox), default=None)
            if track is None or _iou(track.bbox, detection.bbox) < 0.2:
                track = Track(self.next_id, detection.camera_id, detection.sector,
                              detection.object_class, detection.confidence,
                              detection.bbox, now_ms, now_ms)
                self.tracks[self.next_id] = track
                self.next_id += 1
            else:
                old_area = track.bbox.width * track.bbox.height
                new_area = detection.bbox.width * detection.bbox.height
                track.approaching = new_area > old_area * 1.01
                alpha = 0.65
                track.bbox = BoundingBox(
                    alpha * detection.bbox.x + (1-alpha) * track.bbox.x,
                    alpha * detection.bbox.y + (1-alpha) * track.bbox.y,
                    alpha * detection.bbox.width + (1-alpha) * track.bbox.width,
                    alpha * detection.bbox.height + (1-alpha) * track.bbox.height)
                track.confidence = alpha * detection.confidence + (1-alpha) * track.confidence
                track.last_seen_ms = now_ms
                track.consecutive += 1
            track.confidence_history = (track.confidence_history + [detection.confidence])[-16:]
            track.bbox_history = (track.bbox_history + [detection.bbox])[-16:]
            old_enough = now_ms - track.first_seen_ms >= self.policy["minimumTrackAgeMs"]
            in_window = now_ms - track.first_seen_ms <= self.policy["confirmationWindowMs"]
            track.confirmed = track.confirmed or (
                detection.object_class.value == "drone"
                and track.confidence >= self.policy["minimumConfidence"]
                and track.consecutive >= self.policy["confirmationFrames"]
                and old_enough and in_window)
            updated.append(track)
        self.expire(now_ms)
        return updated

    def expire(self, now_ms: int) -> list[int]:
        expired = [track_id for track_id, track in self.tracks.items()
                   if now_ms - track.last_seen_ms > self.policy["trackTimeoutMs"]]
        self.last_expired = [self.tracks[track_id] for track_id in expired]
        for track_id in expired:
            del self.tracks[track_id]
        return expired
