"""Export a trained full-frame detector to ONNX; TensorRT build runs on Jetson."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ml/exports"))
    args = parser.parse_args()
    if not args.checkpoint.is_file():
        raise SystemExit("CHECKPOINT_REQUIRED")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("ULTRALYTICS_REQUIRED") from exc
    args.output.mkdir(parents=True, exist_ok=True)
    exported = Path(YOLO(str(args.checkpoint)).export(format="onnx", opset=17, simplify=True))
    destination = args.output / exported.name
    if exported.resolve() != destination.resolve():
        destination.write_bytes(exported.read_bytes())
    metadata = {"sourceCheckpoint": str(args.checkpoint), "onnx": str(destination),
                "sha256": sha256(destination), "tensorrtStatus": "NOT BUILT — JETSON REQUIRED"}
    (args.output / "export_metadata.json").write_text(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
