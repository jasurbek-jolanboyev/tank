from __future__ import annotations

import json

from app.models import RangeMeasurement, SECTORS


def decode_message(line: str) -> dict:
    message = json.loads(line)
    if message.get("protocolVersion") != 1:
        raise ValueError("unsupported protocol version")
    if not isinstance(message.get("timestamp"), int) or message["timestamp"] < 0:
        raise ValueError("invalid timestamp")
    if "sector" in message and message["sector"] not in SECTORS:
        raise ValueError("invalid sector")
    return message


def decode_range(line: str) -> RangeMeasurement:
    message = decode_message(line)
    if message.get("type") != "range":
        raise ValueError("not a range message")
    distance = message.get("distanceMeters")
    if distance is not None:
        distance = float(distance)
    valid = bool(message.get("valid", False)) and distance is not None and distance > 0
    return RangeMeasurement(message["nodeId"], message["sector"], distance,
                            message["timestamp"], valid, message.get("sensorId"),
                            message.get("signalStrength"), message.get("temperatureC"))


def indicator_message(track, timestamp_ms: int) -> dict:
    return {"protocolVersion": 1, "type": "indicator_state", "timestamp": timestamp_ms,
            "sector": track.sector, "state": track.indicator.value,
            "white": track.indicator.value == "WHITE",
            "red": track.indicator.value == "RED", "trackId": track.track_id}


def safe_off_message(sector: str, timestamp_ms: int) -> dict:
    return {"protocolVersion": 1, "type": "indicator_state", "timestamp": timestamp_ms,
            "sector": sector, "state": "OFF", "white": False, "red": False,
            "trackId": None}
