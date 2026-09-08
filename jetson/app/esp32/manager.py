from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.esp32.protocol import decode_message, decode_range, safe_off_message
from app.esp32.transport import (Esp32Transport, MockEsp32Transport,
                                 SerialEsp32Transport, WebSocketEsp32Transport)

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
            if kind == "mock":
                transport: Esp32Transport = MockEsp32Transport()
            elif kind == "serial":
                transport = SerialEsp32Transport(endpoint, int(config.get("baudRate", config.get("baud", 115200))))
            elif kind == "websocket":
                transport = WebSocketEsp32Transport(endpoint)
            else:  # guarded by configuration validation
                raise ValueError(f"unsupported ESP32 transport: {kind}")
            self.nodes[node_id] = NodeRuntime(node_id, sectors, transport)

    def start(self) -> None:
        self.tasks = [asyncio.create_task(self._receive_loop(node), name=f"esp32:{node.node_id}")
                      for node in self.nodes.values()]

    async def _receive_loop(self, node: NodeRuntime) -> None:
        while True:
            try:
                message = await node.transport.receive()
                node.connected = True
                node.error = None
                if message is None:
                    await asyncio.sleep(0.01)
                    continue
                # Validate objects received by transports just as strictly as serial text.
                validated = decode_message(__import__("json").dumps(message))
                if validated.get("nodeId") not in {None, node.node_id}:
                    raise ValueError(f"node identity mismatch: expected {node.node_id}")
                if validated.get("sector") not in {None, *node.sectors}:
                    raise ValueError(f"node {node.node_id} does not own sector {validated.get('sector')}")
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
            LOG.warning("node=%s send failed: %s", node.node_id, exc)
            return False

    async def stop(self) -> None:
        now = int(time.monotonic() * 1000)
        for node in self.nodes.values():
            for sector in node.sectors:
                try:
                    await node.transport.send(safe_off_message(sector, now))
                except Exception:
                    pass
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await asyncio.gather(*(node.transport.close() for node in self.nodes.values()),
                             return_exceptions=True)

    def health(self) -> dict[str, dict]:
        return {node_id: {"connected": node.connected, "messages": node.messages,
                          "malformed": node.malformed, "reconnects": node.reconnects,
                          "lastMessageMs": node.last_message_ms, "error": node.error}
                for node_id, node in self.nodes.items()}


def range_from_message(message: dict, received_ms: int):
    measurement = decode_range(__import__("json").dumps(message))
    # ESP32 and Ubuntu monotonic clocks have different epochs. Freshness is based on
    # central receive time; the original sensor timestamp remains in raw telemetry.
    measurement.timestamp_ms = received_ms
    return measurement
