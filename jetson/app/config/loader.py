from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml

from app.models import SECTORS


MODES = {"SIMULATOR", "DEVELOPMENT", "UBUNTU_VM_REAL", "JETSON_FUTURE"}


def _expand_environment(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_environment(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_environment(item) for key, item in value.items()}
    return value


def _find_unresolved(value: Any) -> list[str]:
    if isinstance(value, str) and "${" in value:
        return [value]
    if isinstance(value, list):
        return [item for value_item in value for item in _find_unresolved(value_item)]
    if isinstance(value, dict):
        return [item for value_item in value.values() for item in _find_unresolved(value_item)]
    return []


@dataclass(frozen=True, slots=True)
class AppConfig:
    raw: dict[str, Any]
    path: Path

    @property
    def mode(self) -> str:
        return str(self.raw.get("mode", "DEVELOPMENT"))

    @property
    def policy(self) -> dict[str, Any]:
        return dict(self.raw["policy"])

    @property
    def cameras(self) -> list[dict[str, Any]]:
        return list(self.raw.get("cameras", []))

    @property
    def esp32_nodes(self) -> list[dict[str, Any]]:
        return list(self.raw.get("esp32Nodes", self.raw.get("esp32_nodes", [])))

    @property
    def is_real(self) -> bool:
        return self.mode in {"UBUNTU_VM_REAL", "JETSON_FUTURE"}


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).resolve()
    data = _expand_environment(yaml.safe_load(config_path.read_text(encoding="utf-8")))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("configuration version must be 1")
    # Backward compatibility for the original development configuration.
    if data.get("mode") == "DEV_MACOS_MODE":
        data["mode"] = "DEVELOPMENT"
    if data.get("mode", "DEVELOPMENT") not in MODES:
        raise ValueError(f"unsupported application mode: {data.get('mode')}")
    policy = data.get("policy", {})
    if float(policy["nearExitMeters"]) <= float(policy["nearEnterMeters"]):
        raise ValueError("nearExitMeters must exceed nearEnterMeters")
    ids: set[str] = set()
    for camera in data.get("cameras", []):
        if camera["id"] in ids:
            raise ValueError(f"duplicate camera id: {camera['id']}")
        ids.add(camera["id"])
        if camera["sector"] not in SECTORS:
            raise ValueError(f"invalid camera sector: {camera['sector']}")
    node_ids: set[str] = set()
    for node in data.get("esp32Nodes", data.get("esp32_nodes", [])):
        node_id = str(node["nodeId"])
        if node_id in node_ids:
            raise ValueError(f"duplicate ESP32 node id: {node_id}")
        node_ids.add(node_id)
        sectors = node.get("sectors", [node.get("sector")])
        if not sectors or any(sector not in SECTORS for sector in sectors):
            raise ValueError(f"invalid sectors for ESP32 node: {node_id}")
        if node.get("transport") not in {"mock", "serial", "websocket"}:
            raise ValueError(f"invalid ESP32 transport for node: {node_id}")
    if data["mode"] in {"UBUNTU_VM_REAL", "JETSON_FUTURE"}:
        unresolved = _find_unresolved(data)
        if unresolved:
            raise ValueError(f"unresolved environment variables in real config: {unresolved}")
        if data.get("ai", {}).get("type") == "mock":
            raise ValueError("real mode prohibits MockDetector")
        if any(camera.get("type") == "simulated" for camera in data.get("cameras", [])):
            raise ValueError("real mode prohibits simulated cameras")
        if any(node.get("transport") == "mock" for node in data.get("esp32Nodes", data.get("esp32_nodes", []))):
            raise ValueError("real mode prohibits mock ESP32 transports")
    return AppConfig(data, config_path)
