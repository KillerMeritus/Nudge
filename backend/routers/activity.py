"""
Activity router — reads latest scrape from scraper/data/current_activity.json.
During development, returns mock data if the scraper file doesn't exist yet.
"""

import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/activity", tags=["activity"])

SCRAPER_FILE = Path(__file__).parents[2] / "scraper" / "data" / "current_activity.json"

MOCK_ACTIVITY = {
    "app_name": "Terminal",
    "window_title": "nudge — backend — zsh",
    "text_elements": [],
    "timestamp": datetime.now().isoformat(),
}

@router.get("/current")
async def get_current_activity():
    if SCRAPER_FILE.exists():
        try:
            data = json.loads(SCRAPER_FILE.read_text())
            return data
        except Exception:
            pass
    # Scraper not running yet — return mock
    return {**MOCK_ACTIVITY, "timestamp": datetime.now().isoformat()}
