from __future__ import annotations

import asyncio
import time

from app.camera.base import CameraFrame


class OpenCvCamera:
    def __init__(self, config: dict):
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV is required for real camera sources") from exc
        self.cv2, self.config = cv2, config
        self.capture = None
        self.failures = 0
        self.sequence = 0

    def _open(self) -> None:
        cv2, config = self.cv2, self.config
        source = config["source"]
        backend = cv2.CAP_ANY
        if config["type"] == "csi":
            sensor = int(source)
            source = (f"nvarguscamerasrc sensor-id={sensor} ! video/x-raw(memory:NVMM),"
                      f"width={config['width']},height={config['height']},framerate={config['captureFps']}/1 "
                      "! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1")
            backend = cv2.CAP_GSTREAMER
        elif config["type"] in {"usb", "webcam"}:
            # Accept both a numeric OpenCV index (e.g. 0) and a stable Linux
            # device path such as /dev/v4l/by-id/... .
            if isinstance(source, str) and source.strip().isdigit():
                source = int(source.strip())
        self.capture = cv2.VideoCapture(source, backend)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config["width"])
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config["height"])
        self.capture.set(cv2.CAP_PROP_FPS, config["captureFps"])
        if not self.capture.isOpened():
            self.capture.release()
            self.capture = None
            raise ConnectionError(f"unable to open camera {config['id']} ({config['type']})")

    async def read(self) -> CameraFrame | None:
        if self.capture is None:
            await asyncio.to_thread(self._open)
        ok, image = await asyncio.to_thread(self.capture.read)
        if not ok:
            await asyncio.to_thread(self.capture.release)
            self.capture = None
            raise ConnectionError(f"camera read failed: {self.config['id']}")
        self.sequence += 1
        if self.config.get("flip"):
            image = self.cv2.flip(image, 1)
        rotation = int(self.config.get("rotation", 0)) % 360
        if rotation == 90:
            image = self.cv2.rotate(image, self.cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            image = self.cv2.rotate(image, self.cv2.ROTATE_180)
        elif rotation == 270:
            image = self.cv2.rotate(image, self.cv2.ROTATE_90_COUNTERCLOCKWISE)
        return CameraFrame(self.config["id"], self.config["sector"], self.sequence,
                           int(time.monotonic() * 1000), image=image)

    async def close(self) -> None:
        if self.capture is not None:
            await asyncio.to_thread(self.capture.release)
            self.capture = None
