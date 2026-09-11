# Hardware connections

## Central network and cameras

```text
8 PoE RTSP cameras ── Ethernet ── PoE switch ── Ethernet adapter ── MacBook
                                                                       │
                                                         VMware bridged network
                                                                       │
                                                               Ubuntu Server VM
```

Use bridged mode, not host-only mode, when Ubuntu must directly reach camera IPs.
Assign documented static/reserved IPs on an isolated prototype LAN. Confirm each
RTSP URI with `ffprobe` without writing passwords to shell history or Git.

USB bench camera path:

```text
USB UVC camera → USB-C adapter/hub → VMware “Connect to Linux” → /dev/videoX
```

Only one OS can own a passed-through USB device. Enumerate with
`v4l2-ctl --list-devices`; never assume the device remains `/dev/video0`.

## ESP32 link

```text
3.3-V USB-to-TTL adapter → VMware USB passthrough
                               → /dev/ttyACM* or /dev/ttyUSB*
                               → Ubuntu central server
```

Use `/dev/serial/by-id/...` in production configuration when available. The user
running the service needs access to the serial group (normally `dialout`). ESP32
must force all indicator outputs OFF when valid central commands stop for 2 s.

For a dual-Type-C ESP32-S3 board that appears in Ubuntu as `1a86:55d3 QinHeng
USB Single Serial` / `/dev/ttyACM0`, flash with `TANK_USE_UART0_USB_BRIDGE=1`.
Its CH343 USB-UART connector is linked to UART0 GPIO43/44 internally; no extra
serial wires are needed. For boards using a separate 3.3-V UART adapter, retain
the UART2 mode: adapter TX → ESP32 RX16, adapter RX → ESP32 TX15 and GND → GND.
Never use a ±RS-232 adapter directly with ESP32 pins.

## TF02-Pro power and I2C wiring

```text
TF02-Pro red   VCC ── regulated 5 V (not ESP32 3.3 V)
TF02-Pro black GND ── supply GND ── ESP32 GND
TF02-Pro green SCL ── ESP32 profile SCL (GPIO13 placeholder)
TF02-Pro white SDA ── ESP32 profile SDA (GPIO12 placeholder)
```

Set each sensor to I2C mode and a unique saved address before sharing the bus.
Signals are 3.3-V LVTTL. The sensor draws up to 300 mA peak, has no reverse
polarity/over-voltage protection, and must not be powered from a GPIO.

## Full node I²C bus

```text
ESP32 SDA ─┬─ TF02 #1 SDA (unique address)
           ├─ TF02 #2 SDA (unique address)
           ├─ TF02 #3 SDA (unique address)
           └─ TF02 #4 SDA (unique address)
ESP32 SCL ─┴─ matching SCL connections
GND       ─── all grounds
5 V fused ─── all TF02 VCC branches
```

Pull-ups belong on the 3.3-V logic rail and must be calculated for cable length,
bus capacitance and selected speed. Long vehicle cable runs may make bare I²C
unreliable; validate physically or use a suitable differential bus/remote node
architecture. Do not join sensors while they all retain default address 0x10.

## Indicators

Bench LED:

```text
ESP32 GPIO → calculated series resistor → LED → GND
```

External lamp:

```text
ESP32 3.3-V GPIO → compatible driver/isolator → separately fused lamp supply
```

Choose MOSFET, relay, flyback protection and wire gauge from the actual lamp's DC
voltage, steady current and inrush. GPIO never supplies lamp power. Verify `OFF`,
then a small LED, before attaching any higher-power indicator.

## Physical limitations

- VMware USB reconnection can change ownership/device names after suspend.
- Eight USB cameras can exceed hub/controller bandwidth; RTSP/PoE is preferred.
- Bridged Wi-Fi support varies; Ethernet bridging is more predictable.
- CPU inference throughput depends on the eventual ONNX model and VM allocation.
- RTSP introduces encoding/network buffering latency; measure it per camera.
- TF02-Pro has a narrow beam; sharing a sector does not prove its return belongs
  to the object inside a camera bounding box. Mounting/alignment tests are required.
- Total power cannot be specified until camera, lamp, driver and cable choices are final.
