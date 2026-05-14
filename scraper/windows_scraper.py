"""
windows_scraper.py — BE-2
Scrapes the active window's UI element tree using uiautomation.
Extracts meaningful text elements, filters noise, and returns a structured dict
matching the API contract shape for /activity/current.
"""

import uiautomation as auto
import re
import win32gui
import win32process
import psutil
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Filtering constants
# ─────────────────────────────────────────────────────────────────────────────

# Minimum character length for a text element to be kept
MIN_TEXT_LENGTH = 3

# Maximum depth for UI tree walking
WALK_MAX_DEPTH = 50

# Control types whose Name field is almost always noise (icons, containers)
SKIP_CONTROL_TYPES = {
    "PaneControl",
    "GroupControl",
    "ToolBarControl",
    "MenuBarControl",
    "ScrollBarControl",
    "SeparatorControl",
    "ThumbControl",
    "TitleBarControl",
}

# Patterns that indicate UI chrome / boilerplate — not real content
NOISE_PATTERNS = [
    re.compile(r"^\s*$"),                                # blank
    re.compile(r"^[\d\s\W]+$"),                          # only punctuation/numbers
    re.compile(r"Ctrl\+|Alt\+|Shift\+|Win\+"),          # keyboard shortcuts
    re.compile(r"^\d+\s*(x|×)\s*\d+$"),                 # "89 x 19" terminal size
    re.compile(r"^(Ln|Col)\s+\d+"),                      # editor status bar
    re.compile(r"^(UTF|CRLF|LF|Spaces|Tab)"),            # editor encoding/indent
    re.compile(r"Close \(Ctrl", re.IGNORECASE),          # close button label
    re.compile(r"^(Minimize|Maximize|Restore|Close)$", re.IGNORECASE),
    re.compile(r"^(OK|Cancel|Yes|No|Apply)$", re.IGNORECASE),
]

# ─────────────────────────────────────────────────────────────────────────────
# Apps that crash uiautomation's WalkControl (Qt/custom renderers, Electron UIA bugs)
# For these, we capture title + process name only — no element walk.
# ─────────────────────────────────────────────────────────────────────────────
NO_WALK_PROCESS_NAMES = {
    "telegram.exe",           # Qt — UIA provider disconnects mid-walk
    "discord.exe",            # Electron — partial UIA support
    "slack.exe",              # Electron
    "spotify.exe",            # Electron
    "teams.exe",              # Electron/Teams modern
    "ms-teams.exe",
    "notion.exe",             # Electron
    "obsidian.exe",           # Electron
    "signal.exe",             # Electron
    "whatsapp.exe",           # Electron
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_foreground_process_name() -> str:
    """Returns the .exe name of the currently focused process, lowercase."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name().lower()
    except Exception:
        return ""


def _extract_app_name(window_title: str, process_name: str = "") -> str:
    """
    Returns a clean app name.
    Prefers process-name-derived name for known apps,
    otherwise splits the window title on common separators.
    """
    # Well-known process → friendly name map
    KNOWN = {
        "telegram.exe": "Telegram",
        "discord.exe":  "Discord",
        "slack.exe":    "Slack",
        "spotify.exe":  "Spotify",
        "teams.exe":    "Microsoft Teams",
        "ms-teams.exe": "Microsoft Teams",
        "notion.exe":   "Notion",
        "obsidian.exe": "Obsidian",
        "signal.exe":   "Signal",
        "whatsapp.exe": "WhatsApp",
        "code.exe":     "Visual Studio Code",
        "chrome.exe":   "Google Chrome",
        "msedge.exe":   "Microsoft Edge",
        "firefox.exe":  "Firefox",
    }
    if process_name and process_name in KNOWN:
        return KNOWN[process_name]

    # Fallback: strip document name from window title
    for sep in [" - ", " — ", " | "]:
        if sep in window_title:
            return window_title.split(sep)[-1].strip()
    return window_title.strip()


def _is_meaningful(text: str, control_type: str) -> bool:
    """Returns True if the text element carries meaningful content."""
    if not text or len(text) < MIN_TEXT_LENGTH:
        return False
    if control_type in SKIP_CONTROL_TYPES:
        return False
    for pattern in NOISE_PATTERNS:
        if pattern.search(text):
            return False
    return True


def _deduplicate(items: list[str]) -> list[str]:
    """Preserve order while removing exact duplicates."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _safe_walk(window) -> list[str]:
    """
    Walks the UIA element tree with per-element error isolation.
    A crash on one element does NOT abort the entire walk.
    Returns a filtered, deduplicated list of meaningful text strings.
    """
    text_elements: list[str] = []
    try:
        for control, depth in auto.WalkControl(window, maxDepth=WALK_MAX_DEPTH):
            try:
                name = control.Name or ""
                ctrl_type = control.ControlTypeName or ""
                if _is_meaningful(name, ctrl_type):
                    text_elements.append(name)
            except Exception:
                # Bad element — skip it, keep walking
                continue
    except Exception as exc:
        # WalkControl itself failed (UIA provider crash / disconnect)
        print(f"[windows_scraper] WalkControl aborted: {exc}")
    return _deduplicate(text_elements)


# ─────────────────────────────────────────────────────────────────────────────
# Main scraper function
# ─────────────────────────────────────────────────────────────────────────────

def scrape_active_window() -> Optional[dict]:
    """
    Scrapes the currently focused window.

    Returns a dict matching the /activity/current API contract:
    {
        "app_name": str,
        "window_title": str,
        "text_elements": [str, ...],   # filtered, deduplicated
        "timestamp": str               # ISO-8601
    }

    Returns None if the foreground window cannot be obtained.
    For apps in NO_WALK_PROCESS_NAMES, skips the element walk and returns
    metadata only (still logged — we know you were in Telegram).
    """
    process_name = _get_foreground_process_name()

    try:
        window = auto.GetForegroundControl()
    except Exception as exc:
        print(f"[windows_scraper] GetForegroundControl failed: {exc}")
        return None

    if window is None:
        return None

    window_title: str = window.Name or ""
    app_name: str = _extract_app_name(window_title, process_name)

    # ── No-walk apps: capture identity, skip element tree ────────────────────
    if process_name in NO_WALK_PROCESS_NAMES:
        print(f"[windows_scraper] No-walk app detected: {process_name} — skipping element walk.")
        return {
            "app_name": app_name,
            "window_title": window_title,
            "text_elements": [],          # empty — UIA walk skipped intentionally
            "process_name": process_name,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    # ── Normal apps: full element walk ────────────────────────────────────────
    text_elements = _safe_walk(window)

    return {
        "app_name": app_name,
        "window_title": window_title,
        "text_elements": text_elements,
        "process_name": process_name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
