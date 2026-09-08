# Model sources

## Planned base architecture (not downloaded)

- Name: ESPDet-Pico
- Upstream: https://github.com/espressif/esp-detection
- Version: pin required before acquisition
- License: AGPL-3.0 (repository); deployment obligations require review
- SHA256: `NOT_ACQUIRED`
- Architecture: ESP-optimized detector based on YOLO11
- Classes: custom; official examples do **not** provide the required airborne classes
- Input: candidate 224×224, final value depends on memory benchmark
- Original/quantized size: `NOT_MEASURED`
- ESP32-S3: officially supported

## Runtime (not downloaded)

- Name: ESP-DL
- Upstream: https://github.com/espressif/esp-dl
- Candidate version: v3.2.0; pin and checksum required before integration
- License: MIT
- Format: `.espdl`, target-specific INT8 quantization
- ESP32-S3: officially supported; ESP-IDF 5.3+ required

No model binary may enter `models/espdl` until its exact revision, license and
SHA256 are recorded here.

## Training dataset

- Name: Drone Detection Dataset (visible subset)
- Upstream: https://github.com/DroneDetectionThesis/Drone-detection-dataset
- Commit: `442d0c6750708cc221636f7a1fd31cbd8cb0aeb8`
- License: CC0-1.0
- Classes: airplane, bird, drone, helicopter
- Local acquisition: `scripts/acquire_cc0_subset.py`; per-file SHA256 is written
  to `datasets/raw/cc0_visible/SOURCE_MANIFEST.json`
- Acquired subset: 2026-08-20, 15 visible sequences per class, 60 videos plus
  60 MATLAB label files; exact byte counts and hashes are in the manifest. This is a pipeline-validation
  subset and is not sufficient evidence of production accuracy.
