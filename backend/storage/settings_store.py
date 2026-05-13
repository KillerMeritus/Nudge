"""
settings_store.py — JSON-backed settings persistence with file locking.
"""

import json
from pathlib import Path
from filelock import FileLock

SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"
LOCK_FILE     = Path(__file__).parent.parent / "data" / "settings.json.lock"

SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

DEFAULTS = {
    "gemini_api_key": "",
    "work_duration_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "long_break_after_cycles": 4,
    "long_break_enabled": True,
    "launch_on_startup": True,
    "distraction_detection_enabled": True,
    "idle_threshold_seconds": 120,
    "distraction_whitelist": [],
}


def load_settings() -> dict:
    with FileLock(str(LOCK_FILE)):
        if not SETTINGS_FILE.exists():
            return dict(DEFAULTS)
        try:
            stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULTS, **stored}   # fill in any new keys from defaults
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULTS)


def save_settings(settings: dict) -> None:
    with FileLock(str(LOCK_FILE)):
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
