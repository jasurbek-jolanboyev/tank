# Protocol v1

Every newline-delimited serial message and every WebSocket message is one UTF-8
JSON object with `protocolVersion`, `type`, and monotonic `timestamp` fields.
Jetson is the authority for detections and sector/indicator decisions. ESP32 is
the authority for physical range and output health. Unknown message fields must
be ignored for forward compatibility; unsupported protocol versions are rejected.

Serial framing is JSON Lines (`\n`). WebSocket framing is one JSON object per
text frame. See `shared/schemas/protocol-v1.json`.
