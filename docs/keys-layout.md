# Eight KEYS layout

`KEYS` means one physical observation/warning assembly. Each KEYS contains one
camera, one TF02-Pro, optional future radar input, one white channel and one red
channel. Cameras connect to the Ubuntu network; sensor/indicator wiring terminates
at the assigned ESP32 node.

| KEYS | Sector | Camera | ESP32 | LiDAR ID | I2C | White GPIO* | Red GPIO* |
|---|---|---|---|---|---:|---:|---:|
| KEYS-01 | FRONT_1 | CAM_FRONT_1 | NODE-01 | RANGE-FRONT-1 | 0x10 | 4 | 5 |
| KEYS-02 | FRONT_2 | CAM_FRONT_2 | NODE-01 | RANGE-FRONT-2 | 0x11 | 6 | 7 |
| KEYS-03 | RIGHT_1 | CAM_RIGHT_1 | NODE-01 | RANGE-RIGHT-1 | 0x12 | 8 | 9 |
| KEYS-04 | RIGHT_2 | CAM_RIGHT_2 | NODE-01 | RANGE-RIGHT-2 | 0x13 | 10 | 11 |
| KEYS-05 | REAR_1 | CAM_REAR_1 | NODE-02 | RANGE-REAR-1 | 0x10 | 4 | 5 |
| KEYS-06 | REAR_2 | CAM_REAR_2 | NODE-02 | RANGE-REAR-2 | 0x11 | 6 | 7 |
| KEYS-07 | LEFT_1 | CAM_LEFT_1 | NODE-02 | RANGE-LEFT-1 | 0x12 | 8 | 9 |
| KEYS-08 | LEFT_2 | CAM_LEFT_2 | NODE-02 | RANGE-LEFT-2 | 0x13 | 10 | 11 |

`*` GPIO values are unverified placeholders. Confirm the exact ESP32-S3 board,
flash/PSRAM/USB/strap pins and electrical driver before wiring.

## Isolation rule

The central server associates detections and fresh range only when their `sector`
matches. It routes the resulting command to the sole node that owns that sector.
The ESP32 compares the received sector against its four-entry board profile and
changes exactly one indicator pair. Other KEYS retain their previous state.

```text
CAM_LEFT_1 detection + RANGE-LEFT-1
                 ↓
              LEFT_1 decision
                 ↓
NODE-02 → only KEYS-07 white/red channel
```

Each KEYS has an independent command timeout. Missing/invalid commands force that
KEYS to OFF and never fabricate a detection.

## Optional radar

No radar part or electrical interface has been selected, so radar is not presently
implemented. A future radar measurement must include `nodeId`, `sensorId`,
`sector`, validity and timestamp, and must obey the same sector/freshness rules.
Do not connect an unspecified radar until its voltage, interface, protocol, field
of view and regulatory constraints are documented.
