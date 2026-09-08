# Current model status

## `tiny-roi-classifier` 0.3.0-smoke

- Path: `trained/tiny_roi_v0_3/tiny_roi_classifier.torchscript`
- Architecture: custom depthwise-separable 96×96 ROI classifier
- Classes: drone, bird, aircraft
- Training source: CC0 visible-video subset, pinned in `MODEL_SOURCES.md`
- Train/validation/test: 3342 / 1152 / 1194 positive ROI samples
- Best validation accuracy: 0.7309027778
- Independent video-level test accuracy: 0.7428810720
- Checkpoint SHA256: `78aecaf51b2e191e45cae42fb193bc65c2cda9fb51ca6c05fdbd72c585f47168`
- TorchScript SHA256: `8bff34f3c5b0363a0abf34c3e8cea4eb562212136fc73ad596c5b8a29c7ae489`
- TorchScript size: 137,951 bytes
- Host zero-input smoke inference: finite output `[1,3]`, 61.15 ms (single cold measurement)
- Deployment status: **NOT ESP32 READY**; `.espdl` export, quantized accuracy
  comparison, camera ROI generation and on-device benchmarks remain required.

This model must not be described as high-accuracy or production-ready. Its test
accuracy is useful as a verified pipeline baseline, not an acceptance result.

## Full-frame YOLO11n smoke artifact — NOT FOR DEPLOYMENT

- Dataset: `cc0_yolo_v3`, YOLO boxes, verifier status `OK`
- Training: 1 epoch, 2% training fraction, 320×320, batch 8, Intel CPU
- Validation: 1,259 images / 1,152 instances
- Precision: 0.000528
- Recall: 0.170
- mAP50: 0.000472
- mAP50-95: 0.000145
- Validation inference: 38.4 ms/image at 320×320 on the Mac host process
- ONNX: `ml/exports/smoke-e1-f002-s320/best.onnx`
- ONNX SHA256: `501602f444ae7cc97062dba9aa59518c747c19fe847f2bf773760620148caede`
- ONNX input/output: `[1,3,320,320]` → `[1,7,2100]`
- Runtime adapter smoke: PASS using ONNX Runtime CPU

The metrics are intentionally unacceptable because this run only verifies the
training/export/runtime pipeline. Never use this artifact for real detection or
safety decisions. Production requires full-dataset training, independent test-set
evaluation, threshold selection and real-camera validation.
