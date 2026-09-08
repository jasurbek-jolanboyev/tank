from __future__ import annotations

import asyncio
import time
from dataclasses import asdict

from app.ai.mock import MockDetector
from app.ai.onnx_detector import OnnxDetector
from app.ai.tensorrt_detector import TensorRTDetector
from app.camera.manager import CameraManager
from app.config.loader import AppConfig
from app.esp32.manager import Esp32Manager, range_from_message
from app.esp32.protocol import indicator_message
from app.events.store import Event, EventStore
from app.fusion.engine import SensorFusionEngine
from app.health.monitor import HealthMonitor
from app.models import RangeMeasurement
from app.recording.jsonl import JsonlRecorder
from app.telemetry.broker import TelemetryBroker
from app.tracking.manager import TrackManager


class DetectionEngine:
    def __init__(self, config: AppConfig):
        self.config = config
        self.cameras = CameraManager(config.cameras)
        ai = config.raw.get("ai", {"type": "mock"})
        if ai["type"] == "mock":
            self.detector = MockDetector()
        elif ai["type"] == "onnx":
            self.detector = OnnxDetector(ai["model"], output_format=ai["format"],
                                         classes=ai["classes"],
                                         confidence=float(ai.get("confidence", 0.25)),
                                         iou=float(ai.get("iou", 0.45)))
        elif ai["type"] == "tensorrt":
            self.detector = TensorRTDetector(ai["engine"])
        else:
            raise ValueError(f"unsupported detector type: {ai['type']}")
        self.tracker = TrackManager(config.policy)
        self.fusion = SensorFusionEngine(config.policy)
        self.esp32 = Esp32Manager(config.esp32_nodes, self._on_esp32_message)
        self.events = EventStore()
        recording = config.raw.get("recording", {})
        directory = config.path.parent.parent / recording.get("directory", "recordings")
        self.recorder = JsonlRecorder(directory, recording.get("enabled", True),
                                     recording.get("maxBytes", 10_485_760),
                                     recording.get("backupCount", 3))
        self.broker = TelemetryBroker()
        self.health = HealthMonitor()
        self.tasks: list[asyncio.Task] = []
        self.running = False
        self.previous_confirmed: set[int] = set()
        self.previous_indicators: dict[str, str] = {}

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.cameras.start()
        self.esp32.start()
        self.tasks = [asyncio.create_task(self._process(camera_id), name=f"ai:{camera_id}")
                      for camera_id in self.cameras.queues]
        if self.config.mode == "SIMULATOR" or self.config.raw.get("range", {}).get("source") == "mock":
            self.tasks.append(asyncio.create_task(self._mock_range(), name="mock-range"))
        self.tasks.append(asyncio.create_task(self._health_loop(), name="health"))

    async def stop(self) -> None:
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.cameras.stop()
        await self.esp32.stop()

    def _publish(self, message: dict) -> None:
        self.broker.publish(message)
        self.recorder.write(message)

    async def _mock_range(self) -> None:
        distances = [50, 40, 30, 25, 23, 22, 21, 20, 19, 18, 21, 23]
        index = 0
        while True:
            await asyncio.sleep(0.5)
            now = int(time.monotonic() * 1000)
            for camera in self.config.cameras:
                measurement = RangeMeasurement("NODE-SIM-01", camera["sector"],
                                               float(distances[index % len(distances)]), now, True)
                self.fusion.observe_range(measurement)
                self._publish({"protocolVersion": 1, "type": "range", "timestamp": now,
                               "nodeId": measurement.node_id, "sector": measurement.sector,
                               "distanceMeters": measurement.distance_meters, "valid": True,
                               "simulated": True})
            index += 1

    async def _on_esp32_message(self, message: dict) -> None:
        now = int(time.monotonic() * 1000)
        if message["type"] == "range":
            measurement = range_from_message(message, now)
            self.fusion.observe_range(measurement)
            self._publish({**message, "sourceTimestamp": message["timestamp"],
                           "timestamp": now, "simulated": False})
        elif message["type"] in {"node_health", "heartbeat"}:
            self._publish({**message, "sourceTimestamp": message["timestamp"],
                           "timestamp": now, "simulated": False})

    async def _process(self, camera_id: str) -> None:
        queue = self.cameras.queues[camera_id]
        ai_fps = float(self.cameras.configs[camera_id].get("aiFps", 5))
        next_inference = 0.0
        while True:
            frame = await queue.get()
            now = time.monotonic()
            if ai_fps <= 0 or now < next_inference:
                continue
            started = now
            next_inference = now + 1 / ai_fps
            detections = await self.detector.detect(frame)
            self.cameras.mark_processed(camera_id, time.monotonic() - started)
            tracks = self.tracker.update(detections, frame.timestamp_ms)
            for expired in self.tracker.last_expired:
                self.previous_confirmed.discard(expired.track_id)
                self._publish(self.events.add(Event("TRACK_LOST", frame.timestamp_ms,
                                                    expired.sector, expired.track_id)).wire())
                still_active = any(item.confirmed and item.sector == expired.sector
                                   for item in self.tracker.tracks.values())
                if not still_active:
                    from app.esp32.protocol import safe_off_message
                    off = safe_off_message(expired.sector, frame.timestamp_ms)
                    delivered = await self.esp32.send_for_sector(expired.sector, off)
                    self._publish({**off, "type": "sector_state", "state": "OFF",
                                   "simulated": frame.simulated, "delivered": delivered})
            for track in tracks:
                self.fusion.fuse(track, frame.timestamp_ms)
                if track.confirmed and track.track_id not in self.previous_confirmed:
                    self.previous_confirmed.add(track.track_id)
                    event = self.events.add(Event("DRONE_CONFIRMED", frame.timestamp_ms,
                                                  track.sector, track.track_id))
                    self._publish(event.wire())
                message = {
                    "protocolVersion": 1, "type": "vision_detection", "timestamp": frame.timestamp_ms,
                    "nodeId": "JETSON-CENTRAL", "cameraId": track.camera_id,
                    "sector": track.sector, "trackId": track.track_id,
                    "class": track.object_class.value, "confidence": track.confidence,
                    "confirmed": track.confirmed, "approaching": track.approaching,
                    "distanceMeters": track.distance_meters,
                    "distanceEstimated": track.distance_meters is None,
                    "rangeClass": self._range_class(track.distance_meters),
                    "indicator": track.indicator.value, "simulated": frame.simulated,
                    "bbox": {"x": track.bbox.x, "y": track.bbox.y,
                             "w": track.bbox.width, "h": track.bbox.height},
                }
                self._publish(message)
                command = indicator_message(track, frame.timestamp_ms)
                sent = await self.esp32.send_for_sector(track.sector, command)
                self._publish({**command, "type": "sector_state", "state": track.indicator.value,
                               "simulated": frame.simulated, "delivered": sent})
                previous = self.previous_indicators.get(track.sector, "OFF")
                current = track.indicator.value
                if previous != current:
                    if current == "RED":
                        event_name = "ENTERED_NEAR_ZONE"
                    elif previous == "RED" and current == "WHITE":
                        event_name = "LEFT_NEAR_ZONE"
                    else:
                        event_name = None
                    if event_name:
                        self._publish(self.events.add(Event(event_name, frame.timestamp_ms,
                                                           track.sector, track.track_id)).wire())
                    self.previous_indicators[track.sector] = current

    @staticmethod
    def _range_class(distance: float | None) -> str:
        if distance is None:
            return "UNKNOWN"
        if distance <= 20:
            return "NEAR"
        if distance <= 35:
            return "MEDIUM"
        return "FAR"

    async def _health_loop(self) -> None:
        while True:
            await asyncio.sleep(1)
            now = int(time.monotonic() * 1000)
            for camera_id, health in self.cameras.health.items():
                self._publish({"protocolVersion": 1, "type": "camera_health", "timestamp": now,
                               "cameraId": camera_id, **asdict(health)})
            self._publish(self.health.snapshot(self.cameras.health, self.detector.name,
                                               sum(1 for n in self.esp32.nodes.values() if n.connected),
                                               self.config.mode, self.esp32.health()))
