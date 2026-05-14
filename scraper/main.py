"""
main.py — BE-2 Scraper Entry Point
====================================
Runs the full scraper loop as a standalone Python process.
- Platform detection (Windows / macOS)
- Scrapes active window every 30 seconds AND on focus change
- Idle detection — skips scrape if idle beyond threshold
- Whitelist filtering
- Writes current_activity.json on every scrape
- Accumulates in-memory daily log, flushes to daily_log.json
- Midnight reset of daily log
- Distraction detection — compares active window against current task
- Exposes a FastAPI sidecar on port 8081 for BE-1 to read the daily log
- AI backend selectable: gemini (default for testing) or ollama (local)

Usage:
    python main.py
    python main.py --ai-backend gemini --gemini-api-key YOUR_KEY
    python main.py --ai-backend ollama --port 8081 --scrape-interval 30
"""

import sys
import os
import json
import time
import threading
import platform
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
import requests

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nudge.scraper")

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CURRENT_ACTIVITY_PATH = DATA_DIR / "current_activity.json"
DAILY_LOG_PATH = DATA_DIR / "daily_log.json"

# ─── FastAPI sidecar for BE-1 ────────────────────────────────────────────────
# BE-1 can GET http://localhost:8081/log to retrieve the daily log
# BE-1 can GET http://localhost:8081/current to retrieve current activity

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

_app = FastAPI(title="Nudge Scraper Sidecar", version="1.0.0")
_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state (accessed from both FastAPI thread and scraper thread)
_state_lock = threading.Lock()
_current_activity: dict = {}
_daily_log: list[dict] = []

# AI backend config — set during startup, read by /summary/generate endpoint
_ai_config: dict = {
    "backend": "gemini",       # "gemini" | "ollama"
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
    "ollama_model": "gemma3:4b",
}


@_app.get("/health")
def health():
    with _state_lock:
        backend = _ai_config.get("backend", "gemini")
    return {
        "status": "ok",
        "service": "nudge-scraper",
        "ai_backend": backend,
    }


@_app.get("/current")
def get_current():
    """Returns the most recent scrape result (same shape as /activity/current on BE-1)."""
    with _state_lock:
        return dict(_current_activity)


@_app.get("/log")
def get_log():
    """Returns the in-memory daily log list. BE-1 reads this for summary generation."""
    with _state_lock:
        return list(_daily_log)


@_app.get("/log/count")
def get_log_count():
    with _state_lock:
        return {"count": len(_daily_log)}


@_app.post("/summary/generate")
def sidecar_generate_summary():
    """
    Triggers AI summary generation from the current in-memory daily log.
    BE-1 can call this directly, or call its own /summary/generate which
    reads from GET /log.

    Returns the same shape as BE-1's /summary/generate:
        { "summary": str, "score": float, ... }
    """
    with _state_lock:
        log_snapshot = list(_daily_log)
        cfg = dict(_ai_config)

    if not log_snapshot:
        return {"error": "No activity logged yet today.", "summary": None}

    backend = cfg.get("backend", "gemini")

    if backend == "gemini":
        from ai.gemini_client import generate_summary
        result = generate_summary(
            daily_log=log_snapshot,
            model=cfg.get("gemini_model", "gemini-2.0-flash"),
            api_key=cfg.get("gemini_api_key") or None,
        )
    else:  # ollama
        from ai.ollama_client import generate_summary
        result = generate_summary(
            daily_log=log_snapshot,
            model=cfg.get("ollama_model", "gemma3:4b"),
        )

    if result is None:
        return {
            "error": f"AI backend '{backend}' failed to generate summary.",
            "summary": None,
        }

    from datetime import datetime
    result["generated_at"] = datetime.now().isoformat(timespec="seconds")
    result["log_entries"] = len(log_snapshot)
    return result


# ─── Import scraper + support modules ────────────────────────────────────────

def _import_scraper():
    """
    Returns the platform-appropriate scrape function.
    On Windows: windows_scraper.scrape_active_window
    On macOS:   mac_scraper.scrape_active_window (not yet implemented)
    """
    system = platform.system()
    if system == "Windows":
        from windows_scraper import scrape_active_window
        logger.info("Platform: Windows — using uiautomation scraper")
        return scrape_active_window
    elif system == "Darwin":
        try:
            from mac_scraper import scrape_active_window
            logger.info("Platform: macOS — using pyobjc scraper")
            return scrape_active_window
        except ImportError:
            logger.error("mac_scraper not implemented. Install pyobjc first.")
            sys.exit(1)
    else:
        logger.error("Unsupported platform: %s", system)
        sys.exit(1)


# ─── Core scraper loop ───────────────────────────────────────────────────────

def _write_current_activity(activity: dict):
    """Atomically writes current_activity.json (overwrite each scrape)."""
    tmp = CURRENT_ACTIVITY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(activity, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CURRENT_ACTIVITY_PATH)


def _flush_daily_log():
    """Persists the in-memory daily log to daily_log.json."""
    with _state_lock:
        snapshot = list(_daily_log)
    DAILY_LOG_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_tasks_from_be1(be1_base: str = "http://localhost:8080") -> list[dict]:
    """
    Reads tasks.json via BE-1's /tasks endpoint.
    Falls back to empty list if BE-1 is not running.
    """
    try:
        resp = requests.get(f"{be1_base}/tasks", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def _get_active_task(tasks: list[dict]) -> dict | None:
    """Returns the first in-progress or highest-priority Todo task."""
    in_progress = [t for t in tasks if t.get("status") == "In Progress"]
    if in_progress:
        return in_progress[0]
    todo = [t for t in tasks if t.get("status") == "Todo"]
    if todo:
        return todo[0]
    return None


def _detect_distraction(
    activity: dict,
    active_task: dict | None,
    be1_base: str,
):
    """
    Sends a POST to BE-1 /distraction/alert if the current window
    appears unrelated to the active task.
    Simple heuristic: if active_task title words don't appear anywhere in
    app_name or window_title.
    """
    if active_task is None:
        return

    task_keywords = set(active_task.get("title", "").lower().split())
    task_tags = {t.lower() for t in active_task.get("tags", [])}
    all_keywords = task_keywords | task_tags

    window_text = (
        activity.get("app_name", "") + " " + activity.get("window_title", "")
    ).lower()

    # If any keyword matches, not a distraction
    if any(kw in window_text for kw in all_keywords if len(kw) > 2):
        return

    # Common productive app whitelist (not distracting regardless of task)
    ALWAYS_OK_APPS = {
        "visual studio code", "vscode", "pycharm", "intellij", "terminal",
        "powershell", "cmd", "git", "github", "notion", "obsidian",
        "slack", "discord",  # communication tools — adjust to taste
    }
    if any(ok in window_text for ok in ALWAYS_OK_APPS):
        return

    # Fire the alert
    try:
        payload = {
            "app_name": activity.get("app_name", ""),
            "window_title": activity.get("window_title", ""),
            "task_title": active_task.get("title", ""),
            "task_id": active_task.get("id", ""),
            "timestamp": activity.get("timestamp", ""),
        }
        requests.post(f"{be1_base}/distraction/alert", json=payload, timeout=2)
        logger.info(
            "[distraction] Alert fired — off task: %s", activity.get("app_name")
        )
    except Exception:
        pass  # BE-1 might not be running yet — silent fail


def _midnight_reset_if_needed(current_day: list):
    """Returns a new empty list and flushes + archives the old log at midnight."""
    today = date.today().isoformat()
    if not current_day:
        return current_day

    first_entry_day = current_day[0].get("timestamp", "")[:10]
    if first_entry_day and first_entry_day != today:
        # Archive yesterday's log
        archive_path = DATA_DIR / f"daily_log_{first_entry_day}.json"
        archive_path.write_text(
            json.dumps(current_day, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("[midnight-reset] Archived log for %s → %s", first_entry_day, archive_path)
        return []
    return current_day


def run_scraper_loop(
    scrape_fn,
    idle_detector,
    focus_hook,
    scrape_interval: int = 30,
    be1_base: str = "http://localhost:8080",
):
    """
    Main scraper loop.
    Two independent triggers:
      1. Interval     — full scrape every `scrape_interval` seconds.
      2. Focus change — WinEvent hook fires instantly when OS switches focus.
    Idle detection, whitelist, distraction alerts, and midnight reset also run here.
    """
    global _current_activity, _daily_log

    from whitelist import is_whitelisted

    last_scrape_time = 0.0
    log_flush_counter = 0

    logger.info("[scraper-loop] Starting. Interval=%ds", scrape_interval)

    while True:
        time.sleep(0.2)          # short tick — hook fires instantly so we drain fast
        now = time.time()

        # ── Idle guard ────────────────────────────────────────────────────────
        if idle_detector.is_idle():
            logger.debug("[scraper-loop] Idle (%.0fs). Skipping.", idle_detector.idle_seconds())
            focus_hook.consume_change()  # drain stale flag while idle
            continue

        # ── Check triggers ────────────────────────────────────────────────────
        focus_changed = focus_hook.consume_change()          # True = hook fired
        interval_due  = (now - last_scrape_time) >= scrape_interval

        if not focus_changed and not interval_due:
            continue

        # ── Log trigger reason ────────────────────────────────────────────────
        if focus_changed:
            title, _ = focus_hook.last_foreground
            logger.info("[scraper-loop] Focus change → '%s'", title[:70])
        else:
            logger.debug("[scraper-loop] Interval scrape triggered.")

        # ── Full scrape ───────────────────────────────────────────────────────
        result = scrape_fn()
        last_scrape_time = now

        if result is None:
            logger.warning("[scraper-loop] Scrape returned None. Skipping.")
            continue

        app_name     = result.get("app_name", "")
        window_title = result.get("window_title", "")

        # ── Whitelist check ───────────────────────────────────────────────────
        if is_whitelisted(app_name, window_title):
            logger.info("[scraper-loop] Whitelisted — skipping: %s", app_name)
            continue

        # ── Update shared state + persist ─────────────────────────────────────
        with _state_lock:
            _current_activity = result
            _daily_log = _midnight_reset_if_needed(_daily_log)
            _daily_log.append(result)

        _write_current_activity(result)

        log_flush_counter += 1
        if log_flush_counter % 10 == 0:
            _flush_daily_log()

        # ── Distraction detection ─────────────────────────────────────────────
        tasks = _load_tasks_from_be1(be1_base)
        active_task = _get_active_task(tasks)
        _detect_distraction(result, active_task, be1_base)

    # Final flush — called via atexit, not reached in normal flow
    _flush_daily_log()






# ─── FastAPI server thread ────────────────────────────────────────────────────

def _run_api_server(port: int):
    uvicorn.run(_app, host="127.0.0.1", port=port, log_level="warning")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nudge Scraper — BE-2")
    parser.add_argument("--port", type=int, default=8081, help="Port for scraper sidecar API")
    parser.add_argument("--scrape-interval", type=int, default=30, help="Seconds between scrapes")
    parser.add_argument("--idle-threshold", type=int, default=120, help="Idle threshold in seconds")
    parser.add_argument("--be1-base", type=str, default="http://localhost:8080", help="BE-1 FastAPI base URL")
    # ── AI backend ──────────────────────────────────────────────────────────
    parser.add_argument(
        "--ai-backend",
        choices=["gemini", "ollama"],
        default="gemini",
        help="AI backend for summary generation: 'gemini' (default) or 'ollama'",
    )
    parser.add_argument(
        "--gemini-api-key",
        type=str,
        default="",
        help="Google Gemini API key (overrides GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--gemini-model",
        type=str,
        default="gemini-2.0-flash",
        help="Gemini model ID (default: gemini-2.0-flash)",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="gemma3:4b",
        help="Ollama model name (default: gemma3:4b)",
    )
    args = parser.parse_args()

    # ── Configure AI backend ─────────────────────────────────────────────────
    import os
    resolved_key = args.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    with _state_lock:
        _ai_config["backend"] = args.ai_backend
        _ai_config["gemini_api_key"] = resolved_key
        _ai_config["gemini_model"] = args.gemini_model
        _ai_config["ollama_model"] = args.ollama_model

    logger.info("[startup] AI backend: %s", args.ai_backend)
    if args.ai_backend == "gemini":
        if not resolved_key:
            logger.warning(
                "[startup] No GEMINI_API_KEY set — /summary/generate will fail. "
                "Pass --gemini-api-key or set the GEMINI_API_KEY environment variable."
            )
        else:
            logger.info("[startup] Gemini model: %s", args.gemini_model)
    else:
        logger.info("[startup] Ollama model: %s", args.ollama_model)

    # ── Idle detector ────────────────────────────────────────────────────────
    from idle_detector import IdleDetector
    idle = IdleDetector(threshold_seconds=args.idle_threshold)
    idle.start()
    logger.info("[startup] Idle detector started (threshold=%ds)", args.idle_threshold)

    # Import platform scraper
    scrape_fn = _import_scraper()

    # Load existing daily log from disk (in case of restart mid-day)
    global _daily_log
    if DAILY_LOG_PATH.exists():
        try:
            existing = json.loads(DAILY_LOG_PATH.read_text(encoding="utf-8"))
            if isinstance(existing, list) and existing:
                today = date.today().isoformat()
                todays_entries = [e for e in existing if e.get("timestamp", "")[:10] == today]
                with _state_lock:
                    _daily_log = todays_entries
                logger.info("[startup] Loaded %d existing log entries from disk", len(todays_entries))
        except Exception as exc:
            logger.warning("[startup] Could not load daily_log.json: %s", exc)

    # ── Focus hook (WinEvent — instant, no UIA polling) ─────────────────
    from focus_hook import FocusHook
    focus_hook = FocusHook()
    focus_hook.start()
    logger.info("[startup] WinEvent focus hook started.")

    # ── Start FastAPI sidecar ────────────────────────────────────────────────
    api_thread = threading.Thread(
        target=_run_api_server,
        args=(args.port,),
        daemon=True,
        name="scraper-api",
    )
    api_thread.start()
    logger.info("[startup] Scraper sidecar API running on http://127.0.0.1:%d", args.port)

    # Register atexit flush
    import atexit
    atexit.register(_flush_daily_log)

    # Run scraper loop (blocking)
    try:
        run_scraper_loop(
            scrape_fn=scrape_fn,
            idle_detector=idle,
            focus_hook=focus_hook,
            scrape_interval=args.scrape_interval,
            be1_base=args.be1_base,
        )
    except KeyboardInterrupt:
        logger.info("[shutdown] KeyboardInterrupt — flushing log and exiting.")
        _flush_daily_log()
        idle.stop()
        focus_hook.stop()
        sys.exit(0)



if __name__ == "__main__":
    main()
