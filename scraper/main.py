#!/usr/bin/env python3
"""
NUDGE SCRAPER — main.py
Entry point. Detects platform, runs the appropriate scraper in a loop.

Run with: python3 scraper/main.py
"""

import sys
import time
import json
import platform
from pathlib import Path
from datetime import datetime

# ── PATHS ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

CURRENT_FILE  = DATA_DIR / "current_activity.json"
DAILY_LOG_FILE = DATA_DIR / "daily_log.json"

# ── PLATFORM DETECTION ────────────────────────────────────────────────────────
PLATFORM = platform.system()   # "Darwin" | "Windows" | "Linux"

if PLATFORM == "Darwin":
    from scraper.mac_scraper import get_active_window
elif PLATFORM == "Windows":
    from scraper.windows_scraper import get_active_window
else:
    print(f"[scraper] Unsupported platform: {PLATFORM}")
    sys.exit(1)

from scraper.idle_detector import is_idle
from scraper.whitelist import is_whitelisted

# ── DAILY LOG ─────────────────────────────────────────────────────────────────
_daily_log: list = []
_current_day: str = datetime.now().strftime("%Y-%m-%d")


def _midnight_reset():
    global _daily_log, _current_day
    today = datetime.now().strftime("%Y-%m-%d")
    if today != _current_day:
        _daily_log = []
        _current_day = today
        DAILY_LOG_FILE.write_text("[]", encoding="utf-8")
        print("[scraper] Midnight reset — daily log cleared.")


def _flush_log():
    DAILY_LOG_FILE.write_text(
        json.dumps(_daily_log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
POLL_INTERVAL = 5  # seconds

def main():
    print(f"[scraper] Starting on {PLATFORM}. Polling every {POLL_INTERVAL}s.")
    while True:
        try:
            _midnight_reset()

            if is_idle():
                print("[scraper] Idle — skipping.")
                time.sleep(POLL_INTERVAL)
                continue

            activity = get_active_window()

            if is_whitelisted(activity.get("app_name", "")):
                print(f"[scraper] Whitelisted: {activity['app_name']}")
                time.sleep(POLL_INTERVAL)
                continue

            entry = {
                **activity,
                "timestamp": datetime.now().isoformat(),
            }

            # Write current snapshot
            CURRENT_FILE.write_text(
                json.dumps(entry, ensure_ascii=False), encoding="utf-8"
            )

            # Append to daily log
            _daily_log.append(entry)
            _flush_log()

            print(f"[scraper] {entry['app_name']} — {entry['window_title']}")

        except KeyboardInterrupt:
            print("[scraper] Stopped.")
            break
        except Exception as e:
            print(f"[scraper] Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
