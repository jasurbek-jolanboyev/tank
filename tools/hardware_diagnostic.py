#!/usr/bin/env python3
"""Independent, opt-in camera and ESP32 bench diagnostics."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def camera_list(_args):
    for path in sorted(Path("/dev").glob("video*")):
        print(path)


def camera_capture(args):
    import cv2
    source = int(args.source) if args.source.isdigit() else args.source
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise SystemExit(f"cannot open camera: {args.source}")
    started, frames, image = time.monotonic(), 0, None
    while time.monotonic() - started < args.seconds:
        ok, image = capture.read()
        if not ok:
            raise SystemExit("camera stopped producing frames")
        frames += 1
    capture.release()
    elapsed = time.monotonic() - started
    if args.output and image is not None:
        if not cv2.imwrite(args.output, image):
            raise SystemExit(f"could not write {args.output}")
    print(json.dumps({"frames": frames, "seconds": elapsed, "fps": frames / elapsed,
                      "resolution": [int(image.shape[1]), int(image.shape[0])]}))


def serial_read(args):
    import serial
    deadline = time.monotonic() + args.seconds
    with serial.Serial(args.device, args.baud, timeout=0.5, exclusive=True) as port:
        while time.monotonic() < deadline:
            line = port.readline()
            if not line:
                continue
            try:
                message = json.loads(line)
                print(json.dumps(message, indent=2))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                print(f"REJECTED malformed frame: {exc}", file=sys.stderr)


def indicator(args):
    if not args.i_understand_this_changes_physical_outputs:
        raise SystemExit("refusing output test without --i-understand-this-changes-physical-outputs")
    import serial
    message = {"protocolVersion": 1, "type": "indicator_state",
               "timestamp": int(time.monotonic() * 1000), "sector": args.sector,
               "state": args.state, "white": args.state == "WHITE",
               "red": args.state == "RED", "trackId": None, "maintenanceTest": True}
    with serial.Serial(args.device, args.baud, timeout=0.5, write_timeout=1, exclusive=True) as port:
        port.write((json.dumps(message, separators=(",", ":")) + "\n").encode())
        port.flush()
    print(f"MAINTENANCE TEST sent: {args.sector} {args.state}")


def model_info(args):
    import hashlib
    import onnxruntime as ort
    path = Path(args.model)
    if not path.is_file():
        raise SystemExit(f"model does not exist: {path}")
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps({"path": str(path.resolve()), "sha256": digest,
        "providers": session.get_providers(),
        "inputs": [{"name": item.name, "shape": item.shape, "type": item.type}
                   for item in session.get_inputs()],
        "outputs": [{"name": item.name, "shape": item.shape, "type": item.type}
                    for item in session.get_outputs()]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(required=True)
    command = commands.add_parser("camera-list"); command.set_defaults(func=camera_list)
    command = commands.add_parser("camera-capture")
    command.add_argument("source"); command.add_argument("--seconds", type=float, default=5)
    command.add_argument("--output"); command.set_defaults(func=camera_capture)
    command = commands.add_parser("esp32-read")
    command.add_argument("device"); command.add_argument("--baud", type=int, default=115200)
    command.add_argument("--seconds", type=float, default=10); command.set_defaults(func=serial_read)
    command = commands.add_parser("indicator-test")
    command.add_argument("device"); command.add_argument("sector")
    command.add_argument("state", choices=["OFF", "WHITE", "RED"])
    command.add_argument("--baud", type=int, default=115200)
    command.add_argument("--i-understand-this-changes-physical-outputs", action="store_true")
    command.set_defaults(func=indicator)
    command = commands.add_parser("model-info")
    command.add_argument("model"); command.set_defaults(func=model_info)
    args = parser.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
