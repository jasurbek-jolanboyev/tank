# Troubleshooting

- `/ws` refuses upgrade: install a Uvicorn WebSocket backend and restart server.
- Camera offline: verify source index/URI and keep the other workers running.
- macOS sees a camera but TANK reports `ffmpeg camera read failed`: the device
  has enumerated but is not delivering a video stream. Close Zoom, FaceTime,
  Photo Booth, OBS and browser camera tabs; then test it alone. For several UVC
  cameras, use a powered USB 3.x hub or split the cameras across separate
  Type-C adapters/controllers. A lower server preview FPS does not by itself
  reduce the native USB stream sent by the camera.
- MacBook internal camera appears in a sector: stop TANK, run the AVFoundation
  list command in `docs/macos-direct.md`, then update only the external source
  mappings. Do not use the index labelled `FaceTime HD Camera (Built-in)`.
- Browser image appears frozen in `macos-relay-light.example.yaml`: expected;
  preview is intentionally 1 FPS while capture and AI continue at 5 FPS and 3
  FPS respectively.
- Range invalid: check 115200 8N1, 3.3-V UART logic, shared ground and checksum.
- LED wrong: keep external lamp disconnected; verify GPIO using a small LED and
  resistor, then review active-high configuration and driver wiring.
- TensorRT unavailable on macOS is expected; build the engine on JetPack.
