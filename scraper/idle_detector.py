#!/usr/bin/env python3
"""
idle_detector.py — Detects mouse/keyboard inactivity.
Returns True if the user has been idle longer than the threshold.
"""

import platform
import subprocess

PLATFORM = platform.system()

# Default — overridden at runtime from settings
DEFAULT_IDLE_THRESHOLD = 120  # seconds


def get_idle_seconds() -> float:
    """Return how many seconds the user has been idle."""
    if PLATFORM == "Darwin":
        return _macos_idle_seconds()
    elif PLATFORM == "Windows":
        return _windows_idle_seconds()
    return 0.0


def is_idle(threshold: int = DEFAULT_IDLE_THRESHOLD) -> bool:
    return get_idle_seconds() >= threshold


def _macos_idle_seconds() -> float:
    try:
        result = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if "HIDIdleTime" in line:
                ns = int(line.split("=")[-1].strip())
                return ns / 1_000_000_000   # nanoseconds → seconds
    except Exception:
        pass
    return 0.0


def _windows_idle_seconds() -> float:
    try:
        import ctypes
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(lii)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    except Exception:
        return 0.0
