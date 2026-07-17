"""Read-only system information -- OS, CPU, memory, disk usage."""

from __future__ import annotations

import platform
from typing import Any

import psutil


def get_system_info() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        disks.append(
            {
                "mountpoint": part.mountpoint,
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
            }
        )

    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "memory_total_gb": round(memory.total / (1024**3), 1),
        "memory_used_percent": memory.percent,
        "disks": disks,
    }
