from __future__ import annotations

import asyncio
import glob
import logging
import os
import time
from dataclasses import dataclass, replace

from app.camera.base import ICameraSource, LatestFrameQueue
from app.camera.simulated import SimulatedCamera
from app.camera.opencv_source import OpenCvCamera

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CameraHealth:
    camera_id: str
    online: bool = False
    frames: int = 0
    errors: int = 0
    dropped: int = 0
    last_frame_ms: int | None = None
    capture_fps: float = 0.0
    processing_fps: float = 0.0
    inference_latency_ms: float = 0.0
    reconnect_count: int = 0
    width: int = 0
    height: int = 0
    source_type: str = "unknown"
    sector: str = "unknown"
    error: str | None = None


class CameraManager:
    def __init__(self, configs: list[dict]):
        configs = self._resolve_auto_sources(configs)
        self.queues: dict[str, LatestFrameQueue] = {}
        self.sources: dict[str, ICameraSource] = {}
        self.health: dict[str, CameraHealth] = {}
        self.tasks: list[asyncio.Task] = []
        self.configs: dict[str, dict] = {}
        self.latest_jpeg: dict[str, bytes] = {}
        self._processing_windows: dict[str, tuple[float, int]] = {}

        for cfg in configs:
            if not cfg.get("enabled", True):
                continue
            camera_id = cfg["id"]
            if cfg["type"] == "simulated":
                source = SimulatedCamera(camera_id, cfg["sector"], cfg.get("captureFps", 10))
            elif cfg["type"] in {"usb", "webcam", "video", "rtsp", "csi"}:
                source = OpenCvCamera(cfg)
            else:
                raise ValueError(f"unsupported camera type: {cfg['type']}")

            self.sources[camera_id] = source
            self.configs[camera_id] = cfg
            self.queues[camera_id] = LatestFrameQueue(1)
            self.health[camera_id] = CameraHealth(
                camera_id,
                width=int(cfg.get("width", 0)),
                height=int(cfg.get("height", 0)),
                source_type=cfg["type"],
                sector=cfg["sector"],
            )
            self._processing_windows[camera_id] = (time.monotonic(), 0)

    @staticmethod
    def _resolve_auto_sources(configs: list[dict]) -> list[dict]:
        """Resolve unique V4L2 capture nodes, preferring physical UVC cameras."""
        stable = sorted(glob.glob("/dev/v4l/by-id/*video-index0"))
        capture_nodes = []
        for path in sorted(glob.glob("/sys/class/video4linux/video*/index")):
            try:
                if open(path, encoding="utf-8").read().strip() == "0":
                    capture_nodes.append(f"/dev/{os.path.basename(os.path.dirname(path))}")
            except OSError:
                continue

        # VMware's virtual camera should not hide physically passed-through hub
        # cameras. Keep it as a last fallback only.
        physical_stable = [item for item in stable if "VMware" not in item]
        virtual_stable = [item for item in stable if "VMware" in item]
        physical_nodes = [item for item in capture_nodes if "video0" != os.path.basename(item)]
        devices = physical_stable + physical_nodes + virtual_stable + capture_nodes
        used: set[str] = set()
        resolved: list[dict] = []
        for config in configs:
            item = dict(config)
            source = str(item.get("source", ""))
            if item.get("type") in {"usb", "webcam"} and source.lower() in {"auto", "discover"}:
                candidate = next((path for path in devices if os.path.realpath(path) not in used), None)
                if candidate is None:
                    raise RuntimeError(f"no unused V4L2 camera found for {item.get('id')}")
                item["source"] = candidate
                used.add(os.path.realpath(candidate))
            resolved.append(item)
        return resolved

    async def _worker(self, camera_id: str) -> None:
        source, queue, health = self.sources[camera_id], self.queues[camera_id], self.health[camera_id]
        window_started, window_frames = time.monotonic(), 0
        last_preview = 0.0

        while True:
            try:
                frame = await asyncio.wait_for(source.read(), timeout=2.0)
                if frame is None:
                    if health.online:
                        health.online = False
                        health.reconnect_count += 1
                    await asyncio.sleep(0.2)
                    continue

                health.online = True
                health.frames += 1
                health.errors = 0
                health.last_frame_ms = frame.timestamp_ms
                health.error = None
                health.dropped = queue.dropped

                queue.put_latest(frame)

                window_frames += 1
                elapsed = time.monotonic() - window_started
                if elapsed >= 1.0:
                    health.capture_fps = round(window_frames / elapsed, 2)
                    window_started, window_frames = time.monotonic(), 0

                preview_fps = float(self.configs[camera_id].get("previewFps", 5))
                now = time.monotonic()
                if frame.image is not None and preview_fps > 0 and (now - last_preview) >= (1.0 / preview_fps):
                    import cv2
                    ok, encoded = await asyncio.to_thread(
                        cv2.imencode, ".jpg", frame.image, [cv2.IMWRITE_JPEG_QUALITY, 75]
                    )
                    if ok:
                        self.latest_jpeg[camera_id] = encoded.tobytes()
                        last_preview = now

            except asyncio.CancelledError:
                raise
            except (asyncio.TimeoutError, Exception) as exc:
                if health.online:
                    health.reconnect_count += 1
                health.online = False
                health.errors += 1
                health.error = str(exc) if str(exc) else exc.__class__.__name__

                logger.warning(
                    f"Camera [{camera_id}] error count={health.errors}: {health.error}"
                )

                backoff = min(4.0, 0.25 * (2 ** min(health.errors, 4)))
                await asyncio.sleep(backoff)

    def mark_processed(self, camera_id: str, elapsed_seconds: float) -> None:
        health = self.health[camera_id]
        latency = elapsed_seconds * 1000.0

        health.inference_latency_ms = (
            latency if health.inference_latency_ms == 0 else 0.8 * health.inference_latency_ms + 0.2 * latency
        )

        started, frames = self._processing_windows[camera_id]
        frames += 1
        elapsed = time.monotonic() - started
        if elapsed >= 1.0:
            health.processing_fps = round(frames / elapsed, 2)
            started, frames = time.monotonic(), 0
        self._processing_windows[camera_id] = (started, frames)

    def get_health_snapshot(self, camera_id: str) -> CameraHealth | None:
        health = self.health.get(camera_id)
        return replace(health) if health else None

    def start(self) -> None:
        self.tasks = [
            asyncio.create_task(self._worker(camera_id), name=f"camera:{camera_id}")
            for camera_id in self.sources
        ]

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        await asyncio.gather(*(source.close() for source in self.sources.values()), return_exceptions=True)
