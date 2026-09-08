#!/usr/bin/env python3
"""Validate YOLO datasets without modifying source images."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, UnidentifiedImageError

SPLITS = ("train", "validation", "test")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def validate(root: Path) -> tuple[dict, int]:
    report = {"status": "OK", "images": 0, "labels": 0, "corrupt": [],
              "duplicates": [], "missing_labels": [], "invalid_boxes": [],
              "leakage": [], "class_counts": {}, "resolutions": {}, "tiny_objects": 0}
    digests, split_digests = defaultdict(list), defaultdict(set)
    classes, resolutions = Counter(), Counter()
    images = [p for split in SPLITS for p in (root / split).rglob("*") if p.suffix.lower() in EXTENSIONS]
    if not images:
        report["status"] = "DATASET_REQUIRED"
        return report, 2
    for image_path in images:
        split = next((s for s in SPLITS if s in image_path.parts), "unknown")
        try:
            data = image_path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            with Image.open(image_path) as image:
                image.verify(); width, height = image.size
            report["images"] += 1; resolutions[f"{width}x{height}"] += 1
            digests[digest].append(str(image_path)); split_digests[digest].add(split)
        except (OSError, UnidentifiedImageError) as error:
            report["corrupt"].append({"file": str(image_path), "error": str(error)}); continue
        label_path = image_path.with_suffix(".txt")
        if not label_path.exists():
            candidate = Path(str(image_path).replace("/images/", "/labels/")).with_suffix(".txt")
            label_path = candidate if candidate.exists() else label_path
        if not label_path.exists(): report["missing_labels"].append(str(image_path)); continue
        report["labels"] += 1
        for line_no, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), 1):
            fields = line.split()
            try:
                cls, x, y, w, h = int(fields[0]), *map(float, fields[1:5])
                if len(fields) != 5 or cls < 0 or not all(0 <= v <= 1 for v in (x,y,w,h)) or w <= 0 or h <= 0 or x-w/2 < 0 or y-h/2 < 0 or x+w/2 > 1 or y+h/2 > 1:
                    raise ValueError("out of normalized bounds")
                classes[str(cls)] += 1
                if w * width < 12 or h * height < 12: report["tiny_objects"] += 1
            except (ValueError, IndexError) as error:
                report["invalid_boxes"].append({"file": str(label_path), "line": line_no, "error": str(error)})
    report["duplicates"] = [paths for paths in digests.values() if len(paths) > 1]
    report["leakage"] = [{"sha256": d, "splits": sorted(s)} for d,s in split_digests.items() if len(s) > 1]
    report["class_counts"] = dict(classes); report["resolutions"] = dict(resolutions)
    if any(report[k] for k in ("corrupt","missing_labels","invalid_boxes","leakage")): report["status"] = "INVALID"
    return report, 0 if report["status"] == "OK" else 1

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True); args = parser.parse_args()
    report, code = validate(args.root)
    out = Path(__file__).resolve().parents[1] / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Dataset report", "", f"Status: **{report['status']}**", "", f"Images: {report['images']}", f"Labels: {report['labels']}", f"Tiny objects: {report['tiny_objects']}", "", "No metrics are fabricated when data is absent."]
    (out / "dataset_report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(report["status"]); return code
if __name__ == "__main__": raise SystemExit(main())

