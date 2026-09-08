from __future__ import annotations

import argparse
import time
from pathlib import Path


def sources(value: str):
    path = Path(value)
    if path.is_dir():
        yield from sorted(p for p in path.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    else:
        yield value


def main() -> int:
    parser = argparse.ArgumentParser(description="ONNX full-frame detector inspection tool")
    parser.add_argument("source", help="image, directory, video path, or webcam index")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("vision_test_output"))
    args = parser.parse_args()
    try:
        import cv2
        import numpy as np
        import onnxruntime as ort
    except ImportError as exc:
        raise SystemExit("VISION_TEST_DEPENDENCIES_REQUIRED") from exc
    if not args.model.is_file():
        raise SystemExit("MODEL_REQUIRED")
    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    input_meta = session.get_inputs()[0]
    args.output.mkdir(parents=True, exist_ok=True)
    processed = 0
    started = time.perf_counter()
    for item in sources(args.source):
        frame = cv2.imread(str(item))
        if frame is None:
            continue
        height = input_meta.shape[2] if isinstance(input_meta.shape[2], int) else 640
        width = input_meta.shape[3] if isinstance(input_meta.shape[3], int) else 640
        image = cv2.resize(frame, (width, height))[:, :, ::-1]
        tensor = np.transpose(image.astype(np.float32) / 255.0, (2, 0, 1))[None]
        outputs = session.run(None, {input_meta.name: tensor})
        # Output decoding is deliberately model-adapter specific; raw shapes are printed.
        print(item, [tuple(output.shape) for output in outputs])
        cv2.imwrite(str(args.output / Path(str(item)).name), frame)
        processed += 1
    elapsed = time.perf_counter() - started
    print(f"processed={processed} fps={processed / elapsed if elapsed else 0:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
