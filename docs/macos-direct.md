# Direct MacBook runtime

Use this mode when VMware cannot pass a USB hub reliably. Disconnect every
camera and the ESP32 from the VM first; a USB device can belong to either macOS
or the VM, never both at once.

On macOS, verify that the devices appear before starting TANK:

```bash
system_profiler SPUSBDataType
ls -l /dev/cu.usb* /dev/cu.usbserial* 2>/dev/null
```

Create the local Python environment and run the host server:

```bash
cd /Users/jasurbek/tank
python3 -m venv jetson/.venv-macos
jetson/.venv-macos/bin/pip install -r jetson/requirements.txt
scripts/run_macos_direct.sh
```

Allow camera access when macOS asks. The default camera indexes are 0–3; change
only `source` values in `jetson/configs/macos-usb4.example.yaml` when macOS
orders cameras differently. The operator console/browser connects to the
MacBook LAN IP on ports 8080 and 8081.

The ESP32 CH343 USB-UART connector should appear as `/dev/cu.usbmodem*` or
`/dev/cu.usbserial*`. Flash it with `TANK_USE_UART0_USB_BRIDGE=1` before
enabling the relay node.
