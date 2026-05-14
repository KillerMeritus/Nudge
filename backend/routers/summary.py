"""
Summary router — calls Gemini API with today's activity log,
returns structured summary.
Latest summary kept in memory (Phase 1, by design).
"""

import logging
logger = logging.getLogger(__name__)

import json
import urllib.request
import urllib.error
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.storage.settings_store import load_settings

router = APIRouter(prefix="/summary", tags=["summary"])

# ── IN-MEMORY STORAGE ────────────────────────────────────────────────────────
_latest_summary = {
    "summary": None,
    "score": None,
    "generated_at": None,
}

# Updated Gemini model (gemini-2.0-flash from origin/main)
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def _build_prompt(activity_log: list) -> str:
    log_text = "\n".join(
        f"- {e.get('timestamp', '')}: "
        f"{e.get('app_name', '')} — "
        f"{e.get('window_title', '')}"
        for e in activity_log
    ) or "No activity data captured yet."

    return f"""
You are a productivity assistant.

Analyse the following activity log and produce a clean productivity summary.

Activity log:
{log_text}

Return:
1. A short daily productivity summary
2. Main distractions
3. One improvement suggestion
4. Productivity score out of 10

At the very end write:
SCORE: X.X
"""


def _call_gemini(prompt: str, api_key: str) -> tuple[str, float]:
    payload = json.dumps({
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}",
        data=payload,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            result = json.loads(raw)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning("Gemini quota exceeded (429).")
            raise HTTPException(
                status_code=429,
                detail="Gemini quota exceeded. Please try again later or use another API key."
            )
        raise

    # Parse Gemini response
    text = (
        result["candidates"][0]
        ["content"]["parts"][0]["text"]
        .strip()
    )

    # Extract score
    score = 5.0

    for line in reversed(text.splitlines()):
        if line.startswith("SCORE:"):
            try:
                score = float(
                    line.split(":")[1].strip()
                )
            except Exception:
                pass

            text = text[: text.rfind("SCORE:")].strip()
            break

    return text, score


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_summary():
    settings = load_settings()
    api_key = settings.get("gemini_api_key", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not set. Add it in Settings."
        )

    # Read daily log from scraper (BE-2's file), fall back to empty list
    from pathlib import Path
    log_file = Path(__file__).parents[2] / "scraper" / "data" / "daily_log.json"
    activity_log = []

    if log_file.exists():
        try:
            activity_log = json.loads(log_file.read_text())
        except Exception as e:
            logger.warning("Could not read daily_log.json: %s", e)

    if not activity_log:
        logger.warning("Summary requested but daily log is empty — scraper may not be running.")
        # Return a graceful placeholder instead of erroring
        placeholder = (
            f"NUDGE DAILY SUMMARY — {datetime.now().strftime('%Y-%m-%d')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "No activity data yet.\n\n"
            "Start working and run the scraper to capture your activity.\n"
            "Then come back and generate your summary."
        )
        _latest_summary["summary"] = placeholder
        _latest_summary["score"] = None
        _latest_summary["generated_at"] = datetime.now().isoformat()
        return dict(_latest_summary)

    logger.info("Generating summary from %d activity entries.", len(activity_log))
    try:
        summary_text, score = _call_gemini(_build_prompt(activity_log), api_key)
    except HTTPException:
        raise  # re-raise 429 from _call_gemini as-is
    except urllib.error.HTTPError as e:
        logger.error("Gemini API HTTP error: %s", e.code)
        raise HTTPException(status_code=502, detail=f"Gemini API error: {e.code}")
    except Exception as e:
        logger.error("Summary generation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to generate summary: {str(e)}")

    _latest_summary["summary"] = summary_text
    _latest_summary["score"] = score
    _latest_summary["generated_at"] = datetime.now().isoformat()
    logger.info("Summary generated — score: %s", score)
    return dict(_latest_summary)


@router.get("/latest")
async def get_latest_summary():
    return dict(_latest_summary)