# ML pipeline

The primary deployment target is now a full-frame Jetson detector exported as
ONNX and built as a TensorRT engine on the target Jetson. Classes are `drone`,
`bird`, and `aircraft`; background/low-confidence detections become unknown at
the application policy layer. Raw datasets stay on the host.

The existing `tiny-roi-classifier` checkpoints are preserved as legacy smoke
experiments. They classify an already-cropped ROI and are not full detectors.

Run dataset validation first:

```bash
python3 ml/scripts/verify_dataset.py --root ml/datasets
```

An empty dataset exits with `DATASET_REQUIRED`; training/export must not proceed.

Full detector entry points:

```bash
python ml/scripts/train_detector.py --config ml/configs/jetson_detector.yaml
python ml/scripts/export_jetson.py checkpoint.pt --output ml/exports
```

No production detector checkpoint, ONNX file, TensorRT engine or production
accuracy result currently exists.
