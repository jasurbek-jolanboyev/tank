# Host vision test

This validates ONNX loading and preprocessing for an image or image directory.
Bounding-box decoding is model-specific and must be added only after a concrete
full detector is trained/exported. The legacy 96x96 ROI classifier is not
accepted as a full-frame detector.

```bash
python tools/vision_test/main.py image.jpg --model ml/exports/detector.onnx
```
