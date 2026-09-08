from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from app.models import BoundingBox, Detection, ObjectClass

LOG = logging.getLogger("AI")


class OnnxDetector:
    name = "onnx-detector"

    def __init__(self, model_path: str, *, output_format: str, classes: list[str],
                 confidence: float = 0.25, iou: float = 0.45):
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("onnxruntime is required for OnnxDetector") from exc
        if output_format not in {"yolo_v5", "yolo_v8"}:
            raise ValueError("ONNX output format must explicitly be yolo_v5 or yolo_v8")
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("opencv-python-headless and numpy are required for ONNX detection") from exc
        self.cv2, self.np = cv2, np
        self.path, self.output_format = path, output_format
        self.classes = [ObjectClass(value) for value in classes]
        self.confidence_threshold, self.iou_threshold = confidence, iou
        self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        input_meta = self.session.get_inputs()[0]
        self.input_name = input_meta.name
        shape = input_meta.shape
        if len(shape) != 4 or not isinstance(shape[2], int) or not isinstance(shape[3], int):
            raise ValueError(f"model must have a fixed NCHW input shape, got {shape}")
        self.input_height, self.input_width = shape[2], shape[3]
        self.version = self.session.get_modelmeta().custom_metadata_map.get("version", "unknown")
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        LOG.info("model=%s version=%s sha256=%s input=%sx%s format=%s providers=%s",
                 path, self.version, self.sha256, self.input_width, self.input_height,
                 output_format, self.session.get_providers())

    async def detect(self, frame):
        if frame.image is None:
            return []
        return await asyncio.to_thread(self._detect_sync, frame)

    def _letterbox(self, image):
        height, width = image.shape[:2]
        scale = min(self.input_width / width, self.input_height / height)
        resized_w, resized_h = round(width * scale), round(height * scale)
        resized = self.cv2.resize(image, (resized_w, resized_h), interpolation=self.cv2.INTER_LINEAR)
        left, top = (self.input_width - resized_w) // 2, (self.input_height - resized_h) // 2
        canvas = self.np.full((self.input_height, self.input_width, 3), 114, dtype=self.np.uint8)
        canvas[top:top + resized_h, left:left + resized_w] = resized
        rgb = self.cv2.cvtColor(canvas, self.cv2.COLOR_BGR2RGB)
        tensor = rgb.astype(self.np.float32) / 255.0
        return self.np.transpose(tensor, (2, 0, 1))[None], scale, left, top, width, height

    def _detect_sync(self, frame):
        tensor, scale, pad_x, pad_y, image_w, image_h = self._letterbox(frame.image)
        outputs = self.session.run(None, {self.input_name: tensor})
        if len(outputs) != 1:
            raise ValueError(f"expected one detector output, got {len(outputs)}")
        rows = self.np.squeeze(outputs[0])
        expected = len(self.classes) + (4 if self.output_format == "yolo_v8" else 5)
        if rows.ndim != 2:
            raise ValueError(f"expected 2D YOLO output after squeeze, got {rows.shape}")
        if rows.shape[0] == expected:
            rows = rows.T
        if rows.shape[1] != expected:
            raise ValueError(f"configured {self.output_format} with {len(self.classes)} classes "
                             f"expects {expected} columns, got {rows.shape}")
        boxes, scores, class_ids = [], [], []
        for row in rows:
            if self.output_format == "yolo_v8":
                class_scores = row[4:]
                class_id = int(class_scores.argmax())
                score = float(class_scores[class_id])
            else:
                class_scores = row[5:]
                class_id = int(class_scores.argmax())
                score = float(row[4] * class_scores[class_id])
            if score < self.confidence_threshold:
                continue
            cx, cy, width, height = map(float, row[:4])
            x = (cx - width / 2 - pad_x) / scale
            y = (cy - height / 2 - pad_y) / scale
            width, height = width / scale, height / scale
            x, y = max(0.0, x), max(0.0, y)
            width, height = min(width, image_w - x), min(height, image_h - y)
            if width > 0 and height > 0:
                boxes.append([x, y, width, height])
                scores.append(score)
                class_ids.append(class_id)
        keep = self.cv2.dnn.NMSBoxes(boxes, scores, self.confidence_threshold,
                                     self.iou_threshold) if boxes else []
        detections = []
        for index in self.np.array(keep).reshape(-1):
            x, y, width, height = boxes[int(index)]
            bbox = BoundingBox(x / image_w, y / image_h, width / image_w, height / image_h)
            detections.append(Detection(
                f"{frame.camera_id}-{frame.sequence}-{int(index)}", frame.camera_id,
                frame.sector, self.classes[class_ids[int(index)]], scores[int(index)], bbox,
                frame.timestamp_ms, self.name, simulated=False))
        return detections
