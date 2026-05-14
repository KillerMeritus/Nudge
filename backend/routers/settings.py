"""
Settings router — read/write settings.json via settings_store.
"""

import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.storage.settings_store import load_settings, save_settings as _save

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    work_duration_minutes: Optional[int] = None
    short_break_minutes: Optional[int] = None
    long_break_minutes: Optional[int] = None
    long_break_after_cycles: Optional[int] = None
    long_break_enabled: Optional[bool] = None
    launch_on_startup: Optional[bool] = None
    distraction_detection_enabled: Optional[bool] = None
    idle_threshold_seconds: Optional[int] = None
    distraction_whitelist: Optional[list[str]] = None


@router.get("")
async def get_settings():
    return load_settings()


@router.post("")
async def update_settings(body: SettingsUpdate):
    current = load_settings()
    updates = body.model_dump(exclude_none=True)
    current.update(updates)
    _save(current)
    logger.info("Settings updated — fields: %s", list(updates.keys()))
    return current
