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

## SoftAP and operator connectivity

The firmware also starts a WPA2 SoftAP named `TANK-SECURE-NET` with password
`Tank12345678` and AP address `192.168.4.1`. `GET /health` and `GET /telemetry`
on that address expose node reachability and the latest JSON line received from
the serial protocol. This is a node diagnostic/telemetry bridge; Ubuntu remains
the owner of camera capture, JPEG preview, AI inference and indicator decisions.

For the Flutter camera console, connect the phone/Mac to a network that can route
to the Ubuntu server and use its address (for example `172.16.246.172`), not the
ESP32 AP address. The ESP32 AP alone cannot route traffic to an Ubuntu VM unless
the host/VM networking is explicitly bridged to that AP. The console's status
chip opens a runtime host editor and retries WebSocket connections with bounded
exponential backoff.

The HTTP bridge intentionally does not forward camera JPEGs through the ESP32:
camera frames can be several megabytes per second and the ESP32 is reserved for
sensor/indicator safety. Use Ubuntu's `/preview/{cameraId}.jpg` endpoint for
frames.
