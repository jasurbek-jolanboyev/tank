# ESP32-S3 four-KEYS I/O node

One universal firmware builds as NODE-01 (KEYS 1–4) or NODE-02 (KEYS 5–8).
Each node reads four uniquely addressed TF02-Pro sensors over I2C and owns four
independent white/red logic-level GPIO pairs. Primary AI decisions remain on the
Ubuntu central server. Default pins in
`main/config/node_config.h` are placeholders and must be reviewed against the
exact board before wiring. External lamps require a separately powered,
fused, 3.3-V-compatible driver; never power them from GPIO.

Host portable core tests:

```bash
cmake -S . -B ../../build/firmware-host
cmake --build ../../build/firmware-host
ctest --test-dir ../../build/firmware-host --output-on-failure
```

ESP-IDF target builds (when ESP-IDF is installed):

```bash
TANK_NODE_PROFILE=1 idf.py build   # NODE-01 / KEYS-01..04
TANK_NODE_PROFILE=2 idf.py build   # NODE-02 / KEYS-05..08
```

For a typical **active-low 8-channel relay module**, build after checking one
relay with a multimeter or small bench lamp:

```bash
TANK_NODE_PROFILE=1 TANK_INDICATOR_ACTIVE_HIGH=0 idf.py build flash monitor
```

`TANK_INDICATOR_ACTIVE_HIGH=1` remains the safe default for active-high MOSFET
drivers. Relay contacts, not an ESP32 pin, switch the 24-V lamp circuit.

## Dual Type-C CH343 server link

The detected `1a86:55d3 QinHeng USB Single Serial` interface is the board's
USB-UART Type-C connector. Build for that connector (Ubuntu will expose it as
`/dev/ttyACM0`) with:

```bash
TANK_NODE_PROFILE=1 TANK_USE_UART0_USB_BRIDGE=1 \
TANK_INDICATOR_ACTIVE_HIGH=0 idf.py build flash monitor
```

This profile uses UART0 GPIO43/44 internally; no separate jumper wires are
needed for the server link. `TANK_USE_UART0_USB_BRIDGE=0` retains the old
external UART2 GPIO15/16 adapter mode.

Erase/reconfigure the build directory when changing profiles so a binary is never
flashed to the wrong node. The build log prints node/profile/key count at boot.
The GPIO map is an **UNVERIFIED BOARD PROFILE** until the exact board is selected.

At boot the node also creates the WPA2 SoftAP `TANK-SECURE-NET` (password
`Tank12345678`, AP IP `192.168.4.1`). `GET /health` and `/telemetry` are
read-only diagnostics. Camera capture and AI stay on Ubuntu; the node receives
JSON indicator commands over serial and forces each owned sector OFF after 2 s
without a valid command.

Before joining four TF02-Pro units on one bus, configure and save unique I2C
addresses 0x10, 0x11, 0x12 and 0x13 one sensor at a time. External 3.3-V I2C
pull-ups are required and must be sized for the physical bus. Current firmware
uses the official 9-byte/cm obtain-data command and non-blocking 100-ms response
wait.
