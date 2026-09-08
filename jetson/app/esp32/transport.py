from __future__ import annotations

import asyncio
import json
import time
from typing import Protocol


class Esp32Transport(Protocol):
    async def send(self, message: dict) -> None: ...
    async def receive(self) -> dict | None: ...
    async def close(self) -> None: ...


class MockEsp32Transport:
    def __init__(self):
        self.sent: list[dict] = []
        self.incoming: asyncio.Queue[dict] = asyncio.Queue(32)
        self.connected = True

    async def send(self, message: dict) -> None:
        if not self.connected:
            raise ConnectionError("mock ESP32 disconnected")
        self.sent.append(message)

    async def receive(self) -> dict | None:
        try:
            return await asyncio.wait_for(self.incoming.get(), timeout=0.1)
        except TimeoutError:
            return None

    async def close(self) -> None:
        self.connected = False


class SerialEsp32Transport:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port, self.baudrate = port, baudrate
        self.serial = None
        self.retry_at = 0.0
        self.failures = 0

    def _ensure_open(self):
        if self.serial and self.serial.is_open:
            return
        if time.monotonic() < self.retry_at:
            raise ConnectionError("serial reconnect backoff")
        try:
            import serial
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.1,
                                        write_timeout=0.5, exclusive=True)
            self.failures = 0
        except Exception:
            self.failures += 1
            self.retry_at = time.monotonic() + min(30, 0.5 * 2 ** min(self.failures, 6))
            raise

    async def send(self, message: dict) -> None:
        def write():
            self._ensure_open()
            self.serial.write((json.dumps(message, separators=(",", ":")) + "\n").encode())
        await asyncio.to_thread(write)

    async def receive(self) -> dict | None:
        def read():
            self._ensure_open()
            line = self.serial.readline()
            return json.loads(line) if line else None
        return await asyncio.to_thread(read)

    async def close(self) -> None:
        serial, self.serial = self.serial, None
        if serial is not None:
            await asyncio.to_thread(serial.close)


class WebSocketEsp32Transport:
    def __init__(self, uri: str):
        self.uri = uri
        self.socket = None

    async def _connect(self):
        if self.socket is None:
            import websockets
            self.socket = await websockets.connect(self.uri, open_timeout=5)

    async def send(self, message: dict) -> None:
        await self._connect()
        try:
            await self.socket.send(json.dumps(message, separators=(",", ":")))
        except Exception:
            self.socket = None
            raise

    async def receive(self) -> dict | None:
        await self._connect()
        try:
            return json.loads(await asyncio.wait_for(self.socket.recv(), timeout=0.1))
        except TimeoutError:
            return None
        except Exception:
            self.socket = None
            raise

    async def close(self) -> None:
        socket, self.socket = self.socket, None
        if socket is not None:
            await socket.close()
