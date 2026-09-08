# Hardware BOM — Ubuntu VM passive prototype

Status: design BOM. Exact camera, ESP32-S3 board, lamp voltage and enclosure are
not yet selected. Power supplies must be sized after those loads are measured.

## Initial one-key bench

| Part | Qty | Requirement / purpose |
|---|---:|---|
| Intel MacBook | 1 | VMware host; already available |
| VMware VM | 1 | Ubuntu Server 24.04 amd64, bridged networking and USB passthrough |
| ESP32-S3 development board | 1 | Native USB Serial/JTAG preferred; exact board/pinout must be recorded |
| Camera | 1 | USB UVC for bench, or ONVIF/RTSP IP camera |
| Benewake TF02-Pro | 1 | Sector range measurement; narrow 3° FoV |
| White 3–5 mm LED | 1 | Logic bench indicator |
| Red 3–5 mm LED | 1 | Logic bench indicator |
| Current-limiting resistor | 2 | Calculate from actual LED forward voltage and selected GPIO current |
| 5 V regulated supply | 1 | TF02-Pro; supply must tolerate its 300 mA peak plus margin |
| USB data cable | 1 | ESP32 ↔ MacBook/VM; must be a data cable |
| 3.3-V USB-to-TTL UART adapter | 1 | Required by current firmware UART2 pins; CP2102/FTDI-class, never RS-232 voltage |
| Breadboard, wire, connectors | as needed | JST 1.25-4P mating lead for TF02-Pro recommended |

## Full eight-key prototype

| Part | Qty | Requirement / purpose |
|---|---:|---|
| ESP32-S3 node | 2 | NODE-01 sectors 1–4; NODE-02 sectors 5–8 |
| 3.3-V USB-to-TTL UART adapter | 2 | Current Ubuntu link until native USB/Wi-Fi transport is implemented |
| RTSP/IP camera | 8 | Prefer PoE and H.264/H.265 RTSP; credentials stored outside Git |
| TF02-Pro | 8 | One per sector, mechanically aligned and calibrated with its camera |
| Managed/unmanaged PoE switch | 1 | At least 8 PoE camera ports plus uplink; PoE budget from chosen cameras |
| Ethernet cables | 9+ | Camera links and MacBook/uplink; installation-rated as required |
| White indicator channel | 8 | LED for bench or externally powered lamp plus driver |
| Red indicator channel | 8 | LED for bench or externally powered lamp plus driver |
| Two-channel driver stages | 8 | 3.3-V logic compatible MOSFET/relay/isolated module selected for lamp load |
| Fuses and holders | per branch | Separate correctly rated protection for cameras, sensors and indicators |
| DC-DC converters | as required | Selected only after input voltage and measured branch loads are known |
| Distribution, enclosure, glands | as required | Fused, strain-relieved and environmentally appropriate |

TF02-Pro official electrical data is 5–12 V input, average current up to 200 mA,
peak 300 mA, and 3.3-V LVTTL communications. It has no reverse-polarity or
over-voltage protection. See the [official TF02-Pro manual](https://en.benewake.com/uploadfiles/2025/04/20250430175509935.pdf).

## Four sensors per ESP32

Do not allocate one UART per sensor: ESP32-S3 has only three UART controllers,
and UART0 is commonly used for programming/logging. The production wiring target
is TF02-Pro I²C with four unique addresses per node (for example 0x10–0x13), a
shared SDA/SCL bus and correctly calculated pull-ups. Each sensor must be
configured and saved individually before joining the shared bus. The official
manual permits addresses 0x01–0x7F and specifies up to 400 kbit/s. ESP32-S3 UART
limits are documented by [Espressif](https://docs.espressif.com/projects/esp-idf/en/release-v5.2/esp32s3/api-reference/peripherals/uart.html).

Current firmware has two selectable four-KEYS profiles, non-blocking I²C polling,
per-sector indicator routing and timeout-safe OFF. It has not been built with
ESP-IDF or hardware-validated and must not be wired as if its placeholder GPIOs
were approved.

## Not included

No actuator, aiming device, RF transmitter/jammer, weapon interface or destructive
countermeasure belongs in this BOM.
