"""
mac_scraper.py — BE-2
macOS equivalent of windows_scraper.py using pyobjc Accessibility API.
Walks the active window's UI element tree, extracts meaningful text elements,
filters noise, and returns a structured dict matching the API contract.
"""

import sys
import re
from datetime import datetime
from typing import Optional, Any

try:
    from AppKit import NSWorkspace
    from ApplicationServices import (
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
        kAXFocusedWindowAttribute,
        kAXTitleAttribute,
        kAXRoleAttribute,
        kAXValueAttribute,
        kAXChildrenAttribute
    )
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Filtering constants (Matching windows_scraper.py)
# ─────────────────────────────────────────────────────────────────────────────

MIN_TEXT_LENGTH = 3
WALK_MAX_DEPTH = 8

# Roles that are generally noise
SKIP_ROLES = {
    "AXScrollArea",
    "AXScrollBar",
    "AXMenuBar",
    "AXMenu",
    "AXMenuItem",
    "AXSeparator",
    "AXToolbar",
    "AXSplitGroup",
    "AXWindow", # Window titles are captured separately
}

NOISE_PATTERNS = [
    re.compile(r"^\s*$"),                                # blank
    re.compile(r"^[\d\s\W]+$"),                          # only punctuation/numbers
    re.compile(r"⌘|⌥|⇧|⌃"),                             # mac keyboard shortcuts
    re.compile(r"^\d+\s*(x|×)\s*\d+$"),                 # "89 x 19" terminal size
    re.compile(r"^(Ln|Col)\s+\d+"),                      # editor status bar
    re.compile(r"^(UTF|CRLF|LF|Spaces|Tab)"),            # editor encoding/indent
    re.compile(r"^(Minimize|Maximize|Close|Zoom)$", re.IGNORECASE),
    re.compile(r"^(OK|Cancel|Yes|No|Apply)$", re.IGNORECASE),
]

NO_WALK_APPS = {
    "com.tdesktop.Telegram",
    "com.hnc.Discord",
    "com.tinyspeck.slackmacgap",
    "com.spotify.client",
    "com.microsoft.teams",
    "com.microsoft.teams2",
    "notion.id",
    "md.obsidian",
    "org.whispersystems.signal-desktop",
    "WhatsApp",
}

def _is_meaningful(text: str, role: str) -> bool:
    if not text or len(text) < MIN_TEXT_LENGTH:
        return False
    if role in SKIP_ROLES:
        return False
    for pattern in NOISE_PATTERNS:
        if pattern.search(text):
            return False
    return True

def _deduplicate(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def _get_ax_attribute(element, attribute: str) -> Any:
    err, val = AXUIElementCopyAttributeValue(element, attribute, None)
    if err == 0:
        return val
    return None

def _walk_ax_tree(element, current_depth: int) -> list[str]:
    if current_depth > WALK_MAX_DEPTH:
        return []

    texts = []
    
    # Try to extract text from this element
    role = _get_ax_attribute(element, kAXRoleAttribute) or ""
    
    title = _get_ax_attribute(element, kAXTitleAttribute)
    if isinstance(title, str) and _is_meaningful(title, role):
        texts.append(title)
        
    value = _get_ax_attribute(element, kAXValueAttribute)
    if isinstance(value, str) and _is_meaningful(value, role) and value != title:
        texts.append(value)
        
    # Traverse children
    children = _get_ax_attribute(element, kAXChildrenAttribute)
    if children:
        for child in children:
            texts.extend(_walk_ax_tree(child, current_depth + 1))
            
    return texts

def scrape_active_window() -> Optional[dict]:
    """
    Scrapes the active window on macOS.
    Returns a dict matching the /activity/current API contract.
    """
    if 'AppKit' not in sys.modules:
        print("[mac_scraper] PyObjC not installed. Please install pyobjc.")
        return None

    workspace = NSWorkspace.sharedWorkspace()
    frontmost_app = workspace.frontmostApplication()
    
    if not frontmost_app:
        return None
        
    app_name = frontmost_app.localizedName() or ""
    bundle_id = frontmost_app.bundleIdentifier() or ""
    pid = frontmost_app.processIdentifier()
    
    app_element = AXUIElementCreateApplication(pid)
    
    # Get focused window
    focused_window = _get_ax_attribute(app_element, kAXFocusedWindowAttribute)
    
    if focused_window:
        window_title = _get_ax_attribute(focused_window, kAXTitleAttribute) or ""
    else:
        window_title = ""
        
    if bundle_id in NO_WALK_APPS or app_name in NO_WALK_APPS:
        print(f"[mac_scraper] No-walk app detected: {app_name} ({bundle_id}) — skipping element walk.")
        return {
            "app_name": app_name,
            "window_title": window_title,
            "text_elements": [],
            "process_name": bundle_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        
    text_elements = []
    if focused_window:
        # Start at depth 1 for the window itself
        text_elements = _walk_ax_tree(focused_window, 1)
        
    text_elements = _deduplicate(text_elements)
    
    return {
        "app_name": app_name,
        "window_title": window_title,
        "text_elements": text_elements,
        "process_name": bundle_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
