"""Local system status — battery, disk, network, uptime."""

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
import time

import psutil

from samaritan.tools._hud import hud_tool


def _battery() -> str:
    try:
        b = psutil.sensors_battery()
    except (AttributeError, NotImplementedError):
        b = None
    if not b:
        return "Battery: n/a (likely a desktop or unsupported platform)"
    plugged = "plugged in" if b.power_plugged else "on battery"
    mins_left = ""
    if b.secsleft not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN, -1):
        mins_left = f", {b.secsleft // 60} min remaining"
    return f"Battery: {b.percent:.0f}% ({plugged}{mins_left})"


def _disk() -> str:
    u = shutil.disk_usage("/")
    gb = 1024**3
    return (
        f"Disk /: {u.used / gb:.1f} GB used / "
        f"{u.total / gb:.1f} GB ({100 * u.used / u.total:.0f}%)"
    )


def _network() -> str:
    parts = []
    try:
        parts.append(f"host {socket.gethostname()}")
    except OSError:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        parts.append(f"ip {s.getsockname()[0]}")
        s.close()
    except OSError:
        parts.append("ip unavailable")
    try:
        out = subprocess.run(
            [
                "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                "-I",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.startswith("SSID:"):
                parts.append(f"ssid {line.split(':', 1)[1].strip()}")
                break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "Network: " + ", ".join(parts)


def _uptime() -> str:
    boot = psutil.boot_time()
    secs = int(time.time() - boot)
    days, rem = divmod(secs, 86400)
    hrs, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    return f"Uptime: {days}d {hrs}h {mins}m"


def _load() -> str:
    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    return (
        f"CPU: {cpu:.0f}% │ RAM: {mem.percent:.0f}% of "
        f"{mem.total / 1024**3:.1f} GB"
    )


@hud_tool(
    description="Return a snapshot of the local machine: battery, disk, network, CPU/RAM, uptime.",
    properties={},
)
def system_status() -> str:
    return "\n".join(
        [
            f"Platform: {platform.system()} {platform.release()} ({platform.machine()})",
            _battery(),
            _disk(),
            _network(),
            _load(),
            _uptime(),
        ]
    )
