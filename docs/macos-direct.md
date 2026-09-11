# Direct MacBook runtime

Use this mode when VMware cannot pass a USB hub reliably. Disconnect every
camera and the ESP32 from the VM first; a USB device can belong to either macOS
or the VM, never both at once.

On macOS, verify that the devices appear before starting TANK:

```bash
system_profiler SPUSBDataType
system_profiler SPCameraDataType
ffmpeg -hide_banner -f avfoundation -list_devices true -i ''
ls -l /dev/cu.usb* /dev/cu.usbserial* 2>/dev/null
```

Create the local Python environment and run the host server:

```bash
cd /Users/jasurbek/tank
python3 -m venv jetson/.venv-macos
jetson/.venv-macos/bin/pip install -r jetson/requirements.txt
scripts/run_macos_direct.sh
```

Allow camera access when macOS asks. Camera indexes are not stable after a USB
hub or adapter is unplugged. On the 2026-09-12 test topology, FaceTime was
index `0` and four external cameras were `1`–`4`; do not assume that order on a
later boot. Never assign a sector to the line labelled `FaceTime HD Camera
(Built-in)`.

For the current four-external-camera topology use:

```bash
cd /Users/jasurbek/tank
TANK_CONFIG=jetson/configs/macos-all-external.example.yaml scripts/run_macos_direct.sh
```

For low-load detection/indicator testing use:

```bash
cd /Users/jasurbek/tank
TANK_CONFIG=jetson/configs/macos-relay-light.example.yaml scripts/run_macos_direct.sh
```

The low-load profile normalizes processing to 320×240 / 5 FPS, analyzes at 3
FPS, and publishes preview at 1 FPS. A preview that appears to update once per
second is intentional; it is not the AI processing rate. On the latest bench
test two of four enumerated external UVC cameras produced stable frames. The
other two were visible to macOS but did not provide frames, which is a USB
hub/bandwidth/native-camera-mode issue rather than a sector decision issue.

The operator console/browser connects to the MacBook LAN IP on ports 8080 and
8081. The browser dashboard displays only cameras that are currently online.

The ESP32 CH343 USB-UART connector should appear as `/dev/cu.usbmodem*` or
`/dev/cu.usbserial*`. Flash it with `TANK_USE_UART0_USB_BRIDGE=1` before
enabling the relay node.
