#!/usr/bin/env bash
set -u

echo "Tank Ubuntu diagnostic (secrets are never printed)"
uname -a
if [[ -r /etc/os-release ]]; then grep -E '^(NAME|VERSION|VERSION_ID)=' /etc/os-release; fi
python3 --version 2>&1 || true
echo "CPU: $(getconf _NPROCESSORS_ONLN 2>/dev/null || echo unknown) logical cores"
free -h 2>/dev/null || true
df -h / 2>/dev/null || true
ip -brief address 2>/dev/null || true
v4l2-ctl --list-devices 2>/dev/null || echo "No V4L2 camera detected (or v4l-utils absent)"
find /dev -maxdepth 1 \( -name 'ttyACM*' -o -name 'ttyUSB*' \) -print 2>/dev/null | sort
lsusb 2>/dev/null || true
echo "Configured environment presence (values hidden):"
env | sed -n 's/^\(TANK_[A-Z0-9_]*\)=.*/\1=SET/p' | sort
