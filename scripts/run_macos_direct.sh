#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${ROOT_DIR}/jetson/.venv-macos/bin/python"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Missing ${VENV_PYTHON}. Create it with: python3 -m venv jetson/.venv-macos && jetson/.venv-macos/bin/pip install -r jetson/requirements.txt" >&2
  exit 1
fi

export TANK_SERVER_HOST="${TANK_SERVER_HOST:-0.0.0.0}"
export TANK_MODEL_PATH="${TANK_MODEL_PATH:-${ROOT_DIR}/ml/exports/smoke-e1-f002-s320/best.onnx}"
export PYTHONPATH="${ROOT_DIR}/jetson"

exec "${VENV_PYTHON}" -m app.main --config "${ROOT_DIR}/jetson/configs/macos-usb4.example.yaml"
