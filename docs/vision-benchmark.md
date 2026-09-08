# Vision benchmark

| Measurement | Result |
|---|---|
| Portable core build/tests | PASS, 1/1 |
| ESP32 firmware build | NOT TESTED — ESP-IDF unavailable |
| ESP-DL model file/size | NOT AVAILABLE |
| ESP32 peak RAM/PSRAM | NOT TESTED |
| Input/inference/FPS | NOT TESTED |
| Full detector precision/recall/mAP | NOT TESTED |
| Camera/range/WebSocket hardware rates | NOT TESTED |

## Host fallback model — measured 2026-08-20

| Measurement | Result |
|---|---|
| Model | tiny ROI classifier 0.3.0-smoke |
| Input/classes | 96×96 RGB; drone/bird/aircraft |
| Checkpoint / TorchScript | 86,782 B / 137,951 B |
| Best validation accuracy | 73.09% |
| Independent video-level test accuracy | 74.29% |
| Training time | 623.90 s, Intel Mac CPU |
| Cold zero-input TorchScript inference | 61.15 ms, one host measurement |
| INT8 / `.espdl` / ESP32 latency | NOT TESTED |

The original template rows remain `NOT TESTED` where no ESP32 measurement or
full detector evaluation exists.
