from __future__ import annotations

import os
import platform
import time


class HealthMonitor:
    def __init__(self):
        self.started = time.monotonic()

    def snapshot(self, camera_health: dict, ai_name: str, esp32_count: int,
                 mode: str | None = None, esp32_health: dict | None = None) -> dict:
        is_jetson = PathExists("/etc/nv_tegra_release")
        metrics = {"cpuPercent": None, "ramPercent": None, "diskPercent": None,
                   "loadAverage": list(os.getloadavg()) if hasattr(os, "getloadavg") else None}
        try:
            import psutil
            metrics.update(cpuPercent=psutil.cpu_percent(), ramPercent=psutil.virtual_memory().percent,
                           diskPercent=psutil.disk_usage("/").percent)
        except ImportError:
            pass
        return {
            "protocolVersion": 1,
            "type": "system_health",
            "timestamp": int(time.monotonic() * 1000),
            "status": "ok",
            "platform": platform.platform(),
            "jetson": is_jetson,
            "mode": mode or ("JETSON_FUTURE" if is_jetson else "DEVELOPMENT"),
            "ai": ai_name,
            "cameraCount": sum(1 for health in camera_health.values() if health.online),
            "esp32Count": esp32_count,
            "esp32Nodes": esp32_health or {},
            "uptimeSeconds": int(time.monotonic() - self.started),
            "pid": os.getpid(),
            "gpu": "NOT AVAILABLE" if not is_jetson else "JETSON METRICS NOT YET SAMPLED",
            **metrics,
        }


def PathExists(path: str) -> bool:
    return os.path.exists(path)
