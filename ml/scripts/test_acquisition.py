#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "datasets/raw/cc0_visible"
manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
assert manifest["commit"] == "442d0c6750708cc221636f7a1fd31cbd8cb0aeb8"
assert manifest["license"] == "CC0-1.0"
assert len(manifest["files"]) == 120
for entry in manifest["files"]:
    path = root / entry["path"]
    assert path.stat().st_size == entry["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
print("acquisition manifest verified: 120/120 files")
