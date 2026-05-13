#!/usr/bin/env python3
"""
mac_scraper.py — Gets active window info on macOS using pyobjc.
Returns: { app_name, window_title, text_elements }
"""

try:
    import AppKit
    _HAS_APPKIT = True
except ImportError:
    _HAS_APPKIT = False


def get_active_window() -> dict:
    if not _HAS_APPKIT:
        return _fallback()

    try:
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        app_name = active_app.localizedName() or "Unknown"

        # Window title via CGWindowList
        import Quartz
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        window_title = ""
        if window_list:
            pid = active_app.processIdentifier()
            for w in window_list:
                if w.get("kCGWindowOwnerPID") == pid and w.get("kCGWindowName"):
                    window_title = w["kCGWindowName"]
                    break

        return {
            "app_name": app_name,
            "window_title": window_title or app_name,
            "text_elements": [],    # Phase 2: Accessibility API depth-8 scrape
        }
    except Exception as e:
        return _fallback(str(e))


def _fallback(reason: str = "pyobjc not available") -> dict:
    """Return basic info using subprocess as a fallback."""
    import subprocess
    try:
        script = 'tell application "System Events" to get name of first process whose frontmost is true'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        app_name = result.stdout.strip() or "Unknown"
    except Exception:
        app_name = "Unknown"

    return {
        "app_name": app_name,
        "window_title": app_name,
        "text_elements": [],
        "_fallback_reason": reason,
    }
