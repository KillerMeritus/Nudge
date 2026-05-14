"""
Timer router — in-memory Pomodoro state.
State resets on server restart (Phase 1, by design).
"""

import logging
logger = logging.getLogger(__name__)

import time
from fastapi import APIRouter
from backend.storage.settings_store import load_settings

router = APIRouter(prefix="/timer", tags=["timer"])

# ── IN-MEMORY STATE ───────────────────────────────────────────────────────────
_state = {
    "status": "idle",            # "running" | "paused" | "idle"
    "session_type": "focus",     # "focus" | "short_break" | "long_break"
    "session_count": 0,
    "started_at": None,          # epoch float when last started/resumed
    "elapsed_seconds": 0,        # seconds accumulated before current start
}


def _session_duration_seconds() -> int:
    settings = load_settings()
    mapping = {
        "focus":       settings.get("work_duration_minutes", 25) * 60,
        "short_break": settings.get("short_break_minutes", 5) * 60,
        "long_break":  settings.get("long_break_minutes", 15) * 60,
    }
    return mapping.get(_state["session_type"], 1500)


def _remaining() -> int:
    total = _session_duration_seconds()
    if _state["status"] == "running":
        elapsed = _state["elapsed_seconds"] + (time.time() - _state["started_at"])
    else:
        elapsed = _state["elapsed_seconds"]
    return max(0, int(total - elapsed))


def _next_session():
    """Advance to the next session type based on session count."""
    settings = load_settings()
    long_break_enabled = settings.get("long_break_enabled", True)
    cycles = settings.get("long_break_after_cycles", 4)

    if _state["session_type"] == "focus":
        _state["session_count"] += 1
        if long_break_enabled and _state["session_count"] % cycles == 0:
            _state["session_type"] = "long_break"
        else:
            _state["session_type"] = "short_break"
    else:
        _state["session_type"] = "focus"

    _state["elapsed_seconds"] = 0
    _state["started_at"] = None


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_timer():
    if _state["status"] == "running":
        return {
            "status": _state["status"],
            "session_type": _state["session_type"],
            "remaining_seconds": _remaining(),
            "session_count": _state["session_count"],
        }
    _state["status"] = "running"
    _state["started_at"] = time.time()
    logger.info("Timer started — session: %s, remaining: %ds", _state["session_type"], _remaining())
    return {
        "status": "running",
        "session_type": _state["session_type"],
        "remaining_seconds": _remaining(),
        "session_count": _state["session_count"],
    }


@router.post("/pause")
async def pause_timer():
    if _state["status"] == "running":
        _state["elapsed_seconds"] += time.time() - _state["started_at"]
        _state["started_at"] = None
        _state["status"] = "paused"
        logger.info("Timer paused — remaining: %ds", _remaining())
    return {"status": _state["status"], "remaining_seconds": _remaining()}


@router.post("/reset")
async def reset_timer():
    _state["status"] = "idle"
    _state["session_type"] = "focus"
    _state["session_count"] = 0
    _state["started_at"] = None
    _state["elapsed_seconds"] = 0
    logger.info("Timer reset to idle.")
    return {"status": "idle"}


@router.get("/status")
async def get_timer_status():
    return {
        "status": _state["status"],
        "session_type": _state["session_type"],
        "remaining_seconds": _remaining(),
        "session_count": _state["session_count"],
    }
