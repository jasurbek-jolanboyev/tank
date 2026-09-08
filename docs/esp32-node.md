# ESP32-S3 four-KEYS node

Each firmware image selects NODE-01 or NODE-02 at build time. A node owns four
sector mappings, four TF02-Pro I2C addresses and four independent white/red GPIO
pairs. Ubuntu remains the only detection/indicator decision authority.

```text
4 × TF02-Pro I2C → checksum parser/filter → sector-tagged JSON → Ubuntu
Ubuntu sector command → owned-sector lookup → exactly one GPIO pair
```

NODE-01 owns FRONT_1, FRONT_2, RIGHT_1 and RIGHT_2. NODE-02 owns REAR_1,
REAR_2, LEFT_1 and LEFT_2. Unknown sectors are rejected. Every KEYS has its own
last-command timer; after 2 seconds without a valid command it returns OFF.

Four sensors on a node use addresses 0x10–0x13. The firmware issues the official
TF02-Pro I2C obtain-data command and waits 100 ms without blocking other KEYS.
Sensor, checksum and driver health are reported per sector.

The current pin table is an unverified profile. ESP-IDF target build and physical
I2C/GPIO/UART tests remain `NOT RUN — HARDWARE/TOOLCHAIN REQUIRED`.
