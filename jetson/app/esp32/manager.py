from __future__ import annotations

import asyncio
import glob
import json
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.esp32.protocol import decode_message, decode_range, safe_off_message
from app.esp32.transport import (
    Esp32Transport,
    MockEsp32Transport,
    SerialEsp32Transport,
    WebSocketEsp32Transport,
)

LOG = logging.getLogger("ESP32")


@dataclass(slots=True)
class NodeRuntime:
    node_id: str
    sectors: tuple[str, ...]
    transport: Esp32Transport
    connected: bool = False
    messages: int = 0
    malformed: int = 0
    reconnects: int = 0
    last_message_ms: int | None = None
    error: str | None = None


class Esp32Manager:
    """Owns independently supervised transports for any configured node count."""

    def __init__(self, configs: list[dict], on_message: Callable[[dict], Awaitable[None]]):
        self.on_message = on_message
        self.nodes: dict[str, NodeRuntime] = {}
        self.tasks: list[asyncio.Task] = []

        for config in configs:
            node_id = str(config["nodeId"])
            sectors = tuple(config.get("sectors", [config.get("sector")]))
            kind = config["transport"]
            endpoint = str(config.get("endpoint", config.get("device", "")))

            if kind == "serial" and endpoint.lower() in {"", "auto", "discover"}:
                endpoint = self._discover_serial_endpoint()

            if kind == "mock":
                transport: Esp32Transport = MockEsp32Transport()
            elif kind == "serial":
                baud = int(config.get("baudRate", config.get("baud", 115200)))
                transport = SerialEsp32Transport(endpoint, baud)
            elif kind == "websocket":
                transport = WebSocketEsp32Transport(endpoint)
            else:
                raise ValueError(f"unsupported ESP32 transport: {kind}")

            self.nodes[node_id] = NodeRuntime(node_id, sectors, transport)

    @staticmethod
    def _discover_serial_endpoint() -> str:
        candidates = (
            sorted(glob.glob("/dev/serial/by-id/*"))
            + sorted(glob.glob("/dev/ttyACM*"))
            + sorted(glob.glob("/dev/ttyUSB*"))
            + sorted(glob.glob("/dev/cu.usbmodem*"))
            + sorted(glob.glob("/dev/cu.usbserial*"))
        )
        if not candidates:
            fallback = "/dev/cu.usbmodem0" if __import__("sys").platform == "darwin" else "/dev/ttyACM0"
            LOG.warning("No physical USB serial ESP32 device found on startup. Using fallback %s", fallback)
            return fallback
        LOG.info(f"Discovered ESP32 serial endpoint: {candidates[0]}")
        return candidates[0]

    def start(self) -> None:
        self.tasks = [
            asyncio.create_task(self._receive_loop(node), name=f"esp32:{node.node_id}")
            for node in self.nodes.values()
        ]

    async def _receive_loop(self, node: NodeRuntime) -> None:
        while True:
            try:
                message = await node.transport.receive()
                if message is None:
                    await asyncio.sleep(0.01)
                    continue

                node.connected = True
                node.error = None

                # JSON string or dict validation
                if isinstance(message, (str, bytes)):
                    validated = decode_message(message)
                else:
                    validated = decode_message(json.dumps(message))

                # Identity and ownership verification
                msg_node = validated.get("nodeId")
                if msg_node not in {None, node.node_id}:
                    raise ValueError(f"node identity mismatch: expected {node.node_id}, got {msg_node}")

                msg_sector = validated.get("sector")
                if msg_sector not in {None, *node.sectors}:
                    raise ValueError(f"node {node.node_id} does not own sector {msg_sector}")

                node.messages += 1
                node.last_message_ms = int(time.monotonic() * 1000)
                await self.on_message(validated)

            except asyncio.CancelledError:
                raise
            except (ValueError, TypeError, KeyError) as exc:
                node.malformed += 1
                node.error = str(exc)
                LOG.warning("node=%s rejected malformed message: %s", node.node_id, exc)
            except Exception as exc:
                was_connected = node.connected
                node.connected = False
                node.error = str(exc)
                if was_connected:
                    node.reconnects += 1
                LOG.warning("node=%s transport error: %s (reconnects: %d)", node.node_id, exc, node.reconnects)
                await asyncio.sleep(0.5)

    async def send_for_sector(self, sector: str, message: dict) -> bool:
        node = next((item for item in self.nodes.values() if sector in item.sectors), None)
        if node is None:
            LOG.error("no ESP32 node configured for sector=%s", sector)
            return False
        try:
            await node.transport.send(message)
            node.connected = True
            node.error = None
            return True
        except Exception as exc:
            node.connected = False
            node.error = str(exc)
            LOG.warning("node=%s send failed for sector=%s: %s", node.node_id, sector, exc)
            return False

    async def stop(self) -> None:
        now = int(time.monotonic() * 1000)
        # Send safe OFF state to all indicators
        for node in self.nodes.values():
            for sector in node.sectors:
                try:
                    await node.transport.send(safe_off_message(sector, now))
                except Exception:
                    pass

        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        await asyncio.gather(
            *(node.transport.close() for node in self.nodes.values()),
            return_exceptions=True
        )

    def health(self) -> dict[str, dict]:
        return {
            node_id: {
                "connected": node.connected,
                "messages": node.messages,
                "malformed": node.malformed,
                "reconnects": node.reconnects,
                "lastMessageMs": node.last_message_ms,
                "error": node.error,
            }
            for node_id, node in self.nodes.items()
        }


def range_from_message(message: dict, received_ms: int):
    raw_json = message if isinstance(message, str) else json.dumps(message)
    measurement = decode_range(raw_json)
    measurement.timestamp_ms = received_ms
    return measurement
