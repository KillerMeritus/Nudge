"""
NUDGE — FastAPI Entry Point
Run with: uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import health, activity, tasks, timer, summary, settings

app = FastAPI(title="Nudge API", version="1.0.0")

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
