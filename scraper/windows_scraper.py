#!/usr/bin/env python3
"""
windows_scraper.py — Gets active window info on Windows using pywin32.
Returns: { app_name, window_title, text_elements }
"""

try:
    import win32gui
    import win32process
    import psutil
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


def get_active_window() -> dict:
    if not _HAS_WIN32:
        return {
            "app_name": "Unknown",
            "window_title": "Unknown",
            "text_elements": [],
            "_fallback_reason": "pywin32/psutil not installed",
        }

    try:
        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        app_name = proc.name().replace(".exe", "")

        return {
            "app_name": app_name,
            "window_title": window_title or app_name,
            "text_elements": [],    # Phase 2: uiautomation depth-8 scrape
        }
    except Exception as e:
        return {
            "app_name": "Unknown",
            "window_title": "Unknown",
            "text_elements": [],
            "_error": str(e),
        }
