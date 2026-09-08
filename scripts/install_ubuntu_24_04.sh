#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: this installer is only for Ubuntu Linux" >&2
  exit 1
fi
if ! grep -q 'Ubuntu 24.04' /etc/os-release; then
  echo "WARNING: designed for Ubuntu 24.04; detected a different Linux release" >&2
fi

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential libgl1 libglib2.0-0 \
  v4l-utils ffmpeg usbutils pciutils

# The service intentionally has no login shell and owns only its runtime data.
if ! id -u tank >/dev/null 2>&1; then
  sudo useradd --system --user-group --home-dir /var/lib/tank --shell /usr/sbin/nologin tank
fi

sudo install -d -o tank -g tank -m 0750 \
  /etc/tank /var/lib/tank /var/lib/tank/recordings /var/log/tank
python3 -m venv "$repo_dir/jetson/.venv-ubuntu"
"$repo_dir/jetson/.venv-ubuntu/bin/pip" install --upgrade pip
"$repo_dir/jetson/.venv-ubuntu/bin/pip" install -r "$repo_dir/jetson/requirements-ubuntu.txt"

sudo install -m 0644 "$repo_dir/jetson/systemd/tank-detection.service" \
  /etc/systemd/system/tank-detection.service
if [[ ! -e /etc/tank/config.yaml ]]; then
  sudo install -o root -g tank -m 0640 \
    "$repo_dir/jetson/configs/ubuntu-server.example.yaml" /etc/tank/config.yaml
fi
if [[ ! -e /etc/tank/tank.env ]]; then
  sudo install -o root -g tank -m 0640 \
    "$repo_dir/jetson/configs/tank.env.example" /etc/tank/tank.env
fi
sudo systemctl daemon-reload

echo "Installed Ubuntu runtime in $repo_dir/jetson/.venv-ubuntu"
echo "Edit /etc/tank/config.yaml and /etc/tank/tank.env before starting the service."
echo "Then run: sudo systemctl start tank-detection"
echo "The service is installed but not enabled automatically."
