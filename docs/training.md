# Training

`ml/scripts/train_detector.py` records deterministic seed/config and invokes an
optional Ultralytics full detector. `export_jetson.py` exports ONNX and records
SHA256. Existing acquisition, preparation, validation, manifests and CC0 source
data are preserved. No new detector was trained in this migration; production
metrics remain unavailable.
