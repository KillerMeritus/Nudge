"""
Distraction router — receives alerts from BE-2 scraper when the active
window doesn't match the user's current task.

Endpoints:
  POST /distraction/alert   ← BE-2 scraper calls this
  GET  /distraction/alerts  ← FE-1 polls this to show notifications
  DELETE /distraction/alerts ← FE-1 calls to clear after displaying
"""

import logging
from collections import deque
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/distraction", tags=["distraction"])

# ── IN-MEMORY STORE ───────────────────────────────────────────────────────────
# Keep the last 50 alerts in a deque (ring buffer).  Resets on server restart.
_MAX_ALERTS = 50
_alerts: deque = deque(maxlen=_MAX_ALERTS)


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class DistractionAlert(BaseModel):
    app_name: str
    window_title: str
    active_task_title: Optional[str] = None   # None if no task is in-progress


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/alert", status_code=201)
async def receive_alert(body: DistractionAlert):
    """
    Called by BE-2 scraper whenever a distraction is detected.
    Stores the alert in memory so FE-1 can poll and surface it.
    """
    entry = {
        **body.model_dump(),
        "timestamp": datetime.now().isoformat(),
        "seen": False,
    }
    _alerts.appendleft(entry)          # newest first
    logger.info(
        "Distraction alert: %s (%s) — active task: %s",
        body.app_name,
        body.window_title,
        body.active_task_title or "none",
    )
    return {"received": True}


@router.get("/alerts")
async def get_alerts(unseen_only: bool = False):
    """
    Returns the stored distraction alerts, newest first.
    Pass ?unseen_only=true to get only alerts not yet acknowledged.
    """
    alerts = list(_alerts)
    if unseen_only:
        alerts = [a for a in alerts if not a["seen"]]
    return alerts


@router.post("/alerts/seen")
async def mark_seen():
    """Mark all current alerts as seen (FE-1 calls after displaying them)."""
    for alert in _alerts:
        alert["seen"] = True
    return {"marked": len(_alerts)}


@router.delete("/alerts")
async def clear_alerts():
    """Clear all stored alerts (hard reset)."""
    count = len(_alerts)
    _alerts.clear()
    logger.info("Distraction alerts cleared (%d removed).", count)
    return {"cleared": count}
