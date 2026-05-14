"""
whitelist.py — BE-2
Apps excluded from scraping entirely.
Covers password managers, banking, and system credential prompts.
"""

# Exact app name matches (case-insensitive substring match against window title + app name)
WHITELISTED_APPS = [
    # Password managers
    "1password",
    "bitwarden",
    "lastpass",
    "dashlane",
    "keepass",
    "keychain",
    "credential",

    # Banking / finance
    "bank",
    "chase",
    "wells fargo",
    "bank of america",
    "capital one",
    "paypal",
    "venmo",
    "mint",
    "robinhood",

    # System credential / auth prompts
    "windows security",
    "user account control",
    "uac",
    "credential manager",
    "sign in",
    "authentication",
    "two-factor",
    "two factor",
    "2fa",
    "verify your identity",
    "consent.exe",
    "logonui",
    "lockapp",

    # VPN / privacy tools
    "nordvpn",
    "expressvpn",
    "mullvad",
    "protonvpn",

    # Sensitive communication (optional — comment out if you want these scraped)
    # "signal",
]


def is_whitelisted(app_name: str, window_title: str) -> bool:
    """
    Returns True if the app or window should be excluded from scraping.
    Checks both app_name and window_title (case-insensitive substring match).
    """
    combined = f"{app_name} {window_title}".lower()
    return any(entry in combined for entry in WHITELISTED_APPS)
