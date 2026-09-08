# Hardware boundaries

Indicator outputs are logical `ON/OFF` requests only. An ESP32 GPIO must not
power an external lamp directly. Voltage, isolation, transistor/MOSFET/relay,
flyback protection, fusing, and supply sizing belong to an independently reviewed
hardware driver profile. This software contains no aiming actuator, interception,
jamming, projectile, or destructive control.

