# Troubleshooting

- `/ws` refuses upgrade: install a Uvicorn WebSocket backend and restart server.
- Camera offline: verify source index/URI and keep the other workers running.
- Range invalid: check 115200 8N1, 3.3-V UART logic, shared ground and checksum.
- LED wrong: keep external lamp disconnected; verify GPIO using a small LED and
  resistor, then review active-high configuration and driver wiring.
- TensorRT unavailable on macOS is expected; build the engine on JetPack.
