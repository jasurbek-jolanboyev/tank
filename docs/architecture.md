# Authoritative architecture

Ubuntu Server is the central detection and decision computer. ESP32-S3 nodes are
deterministic hardware I/O controllers. Flutter is monitoring/presentation only.

```text
cameras → CameraManager → ONNX detector → TrackManager → SensorFusionEngine
                                                           │
TF02-Pro → ESP32 → Esp32Manager → fresh sector range ──────┤
                                                           ▼
                                                  OFF/WHITE/RED policy
                                                           │
                                                ESP32 indicator GPIO
```

Cameras never pass through ESP32. A failed camera does not stop other workers; a
failed ESP32 node degrades its sectors while camera processing continues; loss of
Flutter does not stop detection. ESP32 outputs return OFF when commands time out.

Modes are `SIMULATOR`, `DEVELOPMENT`, `UBUNTU_VM_REAL`, and `JETSON_FUTURE`.
Real modes reject mock detector, camera and ESP32 configuration. Fake range is
legal only when simulator/mock range is explicit.

The `jetson/` directory name remains to avoid breaking imports. ONNX Runtime CPU
is the current Ubuntu backend; TensorRT is an optional future adapter.
