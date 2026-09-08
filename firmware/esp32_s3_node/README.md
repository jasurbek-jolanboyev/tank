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

Erase/reconfigure the build directory when changing profiles so a binary is never
flashed to the wrong node. The build log prints node/profile/key count at boot.
The GPIO map is an **UNVERIFIED BOARD PROFILE** until the exact board is selected.

Before joining four TF02-Pro units on one bus, configure and save unique I2C
addresses 0x10, 0x11, 0x12 and 0x13 one sensor at a time. External 3.3-V I2C
pull-ups are required and must be sized for the physical bus. Current firmware
uses the official 9-byte/cm obtain-data command and non-blocking 100-ms response
wait.
