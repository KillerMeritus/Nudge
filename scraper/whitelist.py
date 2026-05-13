#!/usr/bin/env python3
"""
whitelist.py — Apps that should never appear in the activity log.
Add any app name (case-insensitive, partial match) to WHITELIST.
"""

WHITELIST = [
    # Password managers
    "1Password",
    "Bitwarden",
    "Keychain Access",
    "LastPass",
    "Dashlane",

    # System / auth
    "SecurityAgent",
    "UserNotificationCenter",
    "System Preferences",
    "System Settings",
    "Login Window",

    # Banking (common macOS app names)
    "Bank of America",
    "Chase",
    "Wells Fargo",
]

_LOWER = [name.lower() for name in WHITELIST]


def is_whitelisted(app_name: str) -> bool:
    """Return True if the app_name matches any whitelist entry (case-insensitive, partial)."""
    lower = app_name.lower()
    return any(w in lower for w in _LOWER)
