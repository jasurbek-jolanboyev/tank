#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "usage: $0 detector.onnx detector.engine" >&2
  exit 2
fi
if ! command -v trtexec >/dev/null; then
  echo "NOT RUN — JETSON/JETPACK trtexec required" >&2
  exit 1
fi
trtexec --onnx="$1" --saveEngine="$2" --fp16
