"""
NUDGE — FastAPI Entry Point
Run with: uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload
"""

import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import health, activity, tasks, timer, summary, settings, distraction
from backend.storage.task_store import load_tasks, save_tasks

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── STARTUP: RECURRING TASK RESET ─────────────────────────────────────────────
def _reset_recurring_tasks() -> None:
    """
    On every server start, find recurring tasks that were marked Done
    on a previous day and reset them to Todo so they appear fresh.
    """
    today = date.today().isoformat()
    tasks_list = load_tasks()
    changed = 0

    for task in tasks_list:
        if (
            task.get("is_recurring")
            and task.get("status") == "Done"
            and task.get("completed_at")          # guard against None
            and task["completed_at"][:10] < today  # completed before today
        ):
            task["status"] = "Todo"
            task["completed_at"] = None
            changed += 1

    if changed:
        save_tasks(tasks_list)
        logger.info("Recurring task reset: %d task(s) reset to Todo.", changed)
    else:
        logger.info("Recurring task reset: nothing to reset.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──
    logger.info("Nudge API starting up…")
    _reset_recurring_tasks()
    yield
    # ── shutdown ──
    logger.info("Nudge API shutting down.")

app = FastAPI(title="Nudge API", version="1.0.0", lifespan=lifespan)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow requests from the Tauri/Vite dev server on any localhost port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",   # Tauri dev
        "http://localhost:5173",   # Vite standalone dev
        "tauri://localhost",       # Tauri production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTERS ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(activity.router)
app.include_router(tasks.router)
app.include_router(timer.router)
app.include_router(summary.router)
app.include_router(settings.router)
app.include_router(distraction.router)
