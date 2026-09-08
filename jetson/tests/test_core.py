import asyncio
import json
import tempfile
import unittest
import copy
from pathlib import Path

from app.camera.base import CameraFrame, LatestFrameQueue
from app.config.loader import load_config
from app.config.loader import AppConfig
from app.engine import DetectionEngine
from app.esp32.protocol import decode_range
from app.esp32.manager import Esp32Manager, range_from_message
from app.esp32.transport import MockEsp32Transport, SerialEsp32Transport
from app.fusion.engine import SensorFusionEngine
from app.models import BoundingBox, Detection, ObjectClass, RangeMeasurement, Track
from app.recording.jsonl import JsonlRecorder, replay
from app.tracking.manager import TrackManager


CONFIG = Path(__file__).parents[1] / "configs" / "dev.yaml"


class CoreTests(unittest.TestCase):
    def test_config(self):
        config = load_config(CONFIG)
        self.assertEqual(config.mode, "SIMULATOR")
        self.assertEqual(config.cameras[0]["sector"], "FRONT_1")

    def test_real_mode_rejects_mock_backends(self):
        original = load_config(CONFIG)
        raw = copy.deepcopy(original.raw)
        raw["mode"] = "UBUNTU_VM_REAL"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            import yaml
            path.write_text(yaml.safe_dump(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "MockDetector"):
                load_config(path)

    def test_real_config_requires_environment_secrets(self):
        path = Path(__file__).parents[1] / "configs" / "ubuntu-vm-real.example.yaml"
        with self.assertRaisesRegex(ValueError, "unresolved environment"):
            load_config(path)

    def test_esp32_transport_selection_and_receive_clock(self):
        async def sink(_):
            return None
        manager = Esp32Manager([
            {"nodeId": "MOCK", "sectors": ["FRONT_1"], "transport": "mock"},
            {"nodeId": "SERIAL", "sector": "RIGHT_1", "transport": "serial",
             "endpoint": "/dev/example", "baudRate": 57600},
        ], sink)
        self.assertIsInstance(manager.nodes["MOCK"].transport, MockEsp32Transport)
        serial = manager.nodes["SERIAL"].transport
        self.assertIsInstance(serial, SerialEsp32Transport)
        self.assertEqual(serial.baudrate, 57600)
        measurement = range_from_message({"protocolVersion": 1, "type": "range",
            "timestamp": 12, "nodeId": "SERIAL", "sensorId": "R1",
            "sector": "RIGHT_1", "distanceMeters": 10.5, "valid": True}, 999)
        self.assertEqual(measurement.timestamp_ms, 999)
        self.assertEqual(measurement.sensor_id, "R1")

    def test_eight_keys_are_uniquely_routed(self):
        import os
        keys = {
            "TANK_SERVER_HOST": "127.0.0.1", "TANK_MODEL_PATH": "/tmp/model.onnx",
            "TANK_ESP32_NODE_01_DEVICE": "/dev/node1", "TANK_ESP32_NODE_02_DEVICE": "/dev/node2",
        }
        for sector in ("FRONT_1", "FRONT_2", "RIGHT_1", "RIGHT_2",
                       "REAR_1", "REAR_2", "LEFT_1", "LEFT_2"):
            keys[f"TANK_CAM_{sector}_RTSP"] = f"rtsp://example/{sector}"
        original = {key: os.environ.get(key) for key in keys}
        os.environ.update(keys)
        try:
            config = load_config(Path(__file__).parents[1] / "configs" / "ubuntu-vm-real.example.yaml")
        finally:
            for key, value in original.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value
        camera_sectors = [camera["sector"] for camera in config.cameras]
        owned_sectors = [sector for node in config.esp32_nodes for sector in node["sectors"]]
        self.assertEqual(len(camera_sectors), 8)
        self.assertEqual(set(camera_sectors), set(owned_sectors))
        self.assertEqual(len(owned_sectors), len(set(owned_sectors)))

    def test_latest_queue_drops_stale(self):
        async def run():
            queue = LatestFrameQueue(1)
            queue.put_latest(CameraFrame("C", "FRONT_1", 1, 1))
            queue.put_latest(CameraFrame("C", "FRONT_1", 2, 2))
            self.assertEqual((await queue.get()).sequence, 2)
            self.assertEqual(queue.dropped, 1)
        asyncio.run(run())

    def test_protocol_range(self):
        measurement = decode_range(json.dumps({"protocolVersion": 1, "type": "range",
            "timestamp": 10, "nodeId": "N", "sector": "RIGHT_1",
            "distanceMeters": 18.6, "valid": True}))
        self.assertTrue(measurement.valid)
        self.assertEqual(measurement.distance_meters, 18.6)
        with self.assertRaises(ValueError):
            decode_range('{"protocolVersion":2,"type":"range","timestamp":1}')

    def test_hysteresis(self):
        policy = load_config(CONFIG).policy
        fusion = SensorFusionEngine(policy)
        track = Track(1, "C", "RIGHT_1", ObjectClass.DRONE, .9,
                      BoundingBox(.1, .1, .2, .2), 0, 300,
                      consecutive=3, confirmed=True)
        states = []
        for now, distance in enumerate((30, 19, 21, 23), 1):
            fusion.observe_range(RangeMeasurement("N", "RIGHT_1", distance, now, True))
            track.distance_meters = None
            states.append(fusion.fuse(track, now).indicator.value)
        self.assertEqual(states, ["WHITE", "RED", "RED", "WHITE"])

    def test_tracking_stable_id(self):
        policy = load_config(CONFIG).policy
        tracker = TrackManager(policy)
        ids = []
        for index, now in enumerate((0, 150, 300)):
            detection = Detection(str(index), "C", "FRONT_1", ObjectClass.DRONE,
                                  .9, BoundingBox(.1, .1, .2, .2), now, "test")
            ids.append(tracker.update([detection], now)[0].track_id)
        self.assertEqual(ids, [1, 1, 1])
        self.assertTrue(tracker.tracks[1].confirmed)

    def test_confirmation_is_sticky_until_track_expires(self):
        policy = load_config(CONFIG).policy
        tracker = TrackManager(policy)
        for index, now in enumerate((0, 150, 300, 600, 900, 1200, 1500)):
            detection = Detection(str(index), "C", "FRONT_1", ObjectClass.DRONE,
                                  .9, BoundingBox(.1, .1, .2, .2), now, "test")
            track = tracker.update([detection], now)[0]
        self.assertTrue(track.confirmed)

    def test_record_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = JsonlRecorder(directory)
            recorder.write({"type": "event", "timestamp": 1})
            self.assertEqual(list(replay(Path(directory) / "session.jsonl"))[0]["timestamp"], 1)

    def test_engine_emits_simulated_protocol(self):
        async def run():
            original = load_config(CONFIG)
            raw = copy.deepcopy(original.raw)
            raw["recording"]["enabled"] = False
            engine = DetectionEngine(AppConfig(raw, original.path))
            queue = engine.broker.subscribe()
            await engine.start()
            try:
                messages = [await asyncio.wait_for(queue.get(), 2) for _ in range(3)]
                self.assertTrue(all(message["protocolVersion"] == 1 for message in messages))
                self.assertTrue(any(message["type"] in {"range", "vision_detection"}
                                    for message in messages))
            finally:
                await engine.stop()
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
