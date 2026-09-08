# Ubuntu Server 24.04 VM deployment

Use bridged Ethernet for RTSP cameras. Connect each USB camera and ESP32 to the
Linux guest from VMware; verify `/dev/video*` and `/dev/serial/by-id/*` with
`scripts/diagnose_ubuntu.sh`.

```bash
cd /path/to/tank
scripts/install_ubuntu_24_04.sh
sudoedit /etc/tank/tank.env
sudoedit /etc/tank/config.yaml
scripts/diagnose_ubuntu.sh
```

The installer creates the non-login `tank` service account, its runtime
directories, virtual environment, systemd unit, and initial configuration files
without overwriting an existing configuration. It does not start or enable the
service. The default configuration is a one-USB-camera acceptance baseline;
replace the placeholder camera path and model path in `/etc/tank/tank.env`.
Do not commit RTSP passwords.
Set `TANK_SERVER_HOST` to the VM's address on the isolated bridged prototype LAN
(or `127.0.0.1` for VM-local clients). Restrict that LAN with the host/VM firewall.

No validated full-frame ONNX model is present. `UBUNTU_VM_REAL` cannot perform
real detection until `TANK_MODEL_PATH` points to a compatible, explicitly
configured YOLOv5/v8 ONNX detector.

```bash
sudo systemctl start tank-detection
sudo systemctl stop tank-detection
sudo systemctl status tank-detection
sudo journalctl -u tank-detection -f
sudo systemctl enable tank-detection
sudo systemctl disable tank-detection
```

Enable only after isolated camera, ESP32, range and LED tests pass. Clean shutdown
sends OFF to every configured sector before closing transports.

```bash
scripts/diagnose_ubuntu.sh
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py camera-list
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py camera-capture 0 --output /tmp/camera.jpg
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py esp32-read /dev/serial/by-id/DEVICE
```

Indicator output is deliberately opt-in:

```bash
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py indicator-test \
  /dev/serial/by-id/DEVICE FRONT_1 WHITE \
  --i-understand-this-changes-physical-outputs
```

Send OFF immediately afterward. Begin with a small resistor-limited LED.
`JETSON_FUTURE` retains CSI/TensorRT adapters and is not required by Ubuntu VM.

Run the Mac operator console with the VM address:

```bash
cd apps/operator_console
flutter run -d macos --dart-define=TANK_SERVER_HOST=VM_IP_ADDRESS
```
