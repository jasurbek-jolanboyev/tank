from __future__ import annotations

import asyncio
import time

import numpy as np

from app.camera.base import CameraFrame


class AvFoundationCamera:
    """macOS camera source using FFmpeg's AVFoundation backend directly.

    OpenCV's AVFoundation backend can expose fewer UVC devices than macOS
    itself.  FFmpeg sees the complete AVFoundation device list, including
    identical webcams connected through a hub.
    """

    def __init__(self, config: dict):
        self.config = config
        self.process: asyncio.subprocess.Process | None = None
        self.sequence = 0
        self.frame_bytes = int(config["width"]) * int(config["height"]) * 3

    async def _open(self) -> None:
        width, height = int(self.config["width"]), int(self.config["height"])
        fps = float(self.config.get("captureFps", 15))
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)"
        )
        # captureFps: 0 means preserve the webcam's native maximum frame rate.
        if fps > 0:
            vf += f",fps={fps}"
        input_options: list[str] = []
        if self.config.get("nativeWidth") and self.config.get("nativeHeight"):
            input_options.extend(["-video_size", f"{self.config['nativeWidth']}x{self.config['nativeHeight']}"])
        if self.config.get("nativeFps"):
            input_options.extend(["-framerate", str(self.config["nativeFps"])])
        self.process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "avfoundation", *input_options, "-i", f"{self.config['source']}:none",
            "-vf", vf, "-pix_fmt", "bgr24", "-f", "rawvideo", "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def read(self) -> CameraFrame:
        if self.process is None or self.process.stdout is None:
            await self._open()
        assert self.process is not None and self.process.stdout is not None
        try:
            raw = await self.process.stdout.readexactly(self.frame_bytes)
        except asyncio.IncompleteReadError as exc:
            await self.close()
            raise ConnectionError(f"ffmpeg camera read failed: {self.config['id']}") from exc
        image = np.frombuffer(raw, dtype=np.uint8).reshape(
            (int(self.config["height"]), int(self.config["width"]), 3)
        )
        self.sequence += 1
        return CameraFrame(self.config["id"], self.config["sector"], self.sequence,
                           int(time.monotonic() * 1000), image=image)

    async def close(self) -> None:
        process, self.process = self.process, None
        if process is None:
            return
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
