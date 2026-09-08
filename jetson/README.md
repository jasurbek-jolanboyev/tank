# Jetson central service

macOS development:

```bash
cd /Users/jasurbek/tank/jetson
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python -m app.main
```

The base file is sufficient for simulator mode. For USB/video and ONNX on
macOS, additionally install `requirements-vision-macos.txt`. JetPack provides
its own NVIDIA-compatible OpenCV, CUDA and TensorRT packages; do not replace
them with arbitrary PyPI wheels.

REST health is `http://127.0.0.1:8080/health`; telemetry WebSocket is
`ws://127.0.0.1:8081/ws`. `configs/dev.yaml` uses simulated camera, detector,
range, and ESP32 transport. TensorRT and Jetson hardware metrics are not run on
macOS. The systemd unit is a deployment template and is not installed/enabled
automatically.
