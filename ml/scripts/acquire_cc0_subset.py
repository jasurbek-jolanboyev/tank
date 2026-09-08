#!/usr/bin/env python3
"""Acquire a small, pinned CC0 visible-video subset for pipeline validation."""
from __future__ import annotations
import argparse, hashlib, json, urllib.error, urllib.request
from pathlib import Path

REPOSITORY = "https://github.com/DroneDetectionThesis/Drone-detection-dataset"
COMMIT = "442d0c6750708cc221636f7a1fd31cbd8cb0aeb8"
RAW = f"https://raw.githubusercontent.com/DroneDetectionThesis/Drone-detection-dataset/{COMMIT}/Data/Video_V"
CLASSES = ("DRONE", "BIRD", "AIRPLANE", "HELICOPTER")

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def download(url: str, target: Path) -> bool:
    if target.exists() and target.stat().st_size: return True
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            target.write_bytes(response.read())
        return True
    except urllib.error.HTTPError as error:
        if error.code == 404: return False
        raise

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--per-class", type=int, default=5)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"source": REPOSITORY, "commit": COMMIT, "license": "CC0-1.0", "files": []}
    for class_name in CLASSES:
        acquired = 0
        for index in range(1, 1000):
            if acquired >= args.per_class: break
            stem = f"V_{class_name}_{index:03d}"
            pair = []
            for suffix in (".mp4", "_LABELS.mat"):
                target = args.output / f"{stem}{suffix}"
                if not download(f"{RAW}/{target.name}", target):
                    pair = []; break
                pair.append(target)
            if pair:
                acquired += 1
                for path in pair: manifest["files"].append({"path":path.name,"bytes":path.stat().st_size,"sha256":sha256(path)})
        if acquired < args.per_class: raise RuntimeError(f"Only {acquired} {class_name} sequences found")
    manifest_path = args.output / "SOURCE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(f"acquired {len(manifest['files'])} files; manifest={manifest_path}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
