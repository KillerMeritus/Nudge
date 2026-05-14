"""
Summary router — calls Gemini API with today's activity log, returns structured summary.
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
_latest_summary = {"summary": None, "score": None, "generated_at": None}

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


def _build_prompt(activity_log: list) -> str:
    log_text = "\n".join(
        f"- {e.get('timestamp', '')}: {e.get('app_name', '')} — {e.get('window_title', '')}"
        for e in activity_log
    ) or "No activity data captured yet."

    return f"""You are a productivity assistant. Analyse the following activity log and produce a daily summary.

Activity log:
{log_text}

Output EXACTLY this format (fill in real values, keep the separators):

NUDGE DAILY SUMMARY — {datetime.now().strftime('%Y-%m-%d')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Productivity Score: X.X / 10

What You Worked On:
- [list key activities]

Deep Work Time: X hours Y minutes
Distraction Time: X hours Y minutes

Top Distractions:
- [list top distraction apps/sites]

Biggest Distraction Pattern:
- [one specific pattern observed]

One Suggestion for Tomorrow:
- [one specific, actionable suggestion]

After the formatted summary, output a line: SCORE: X.X (just the number)"""


def _call_gemini(prompt: str, api_key: str) -> tuple[str, float]:
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Extract score from last line
    score = 5.0
    for line in reversed(text.splitlines()):
        if line.startswith("SCORE:"):
            try:
                score = float(line.split(":")[1].strip())
            except ValueError:
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
        raise HTTPException(status_code=503, detail="Gemini API key not set. Add it in Settings.")

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
