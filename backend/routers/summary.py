"""
Summary router — calls Gemini API with today's activity log,
returns structured summary.
Latest summary kept in memory (Phase 1, by design).
"""

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

# Updated Gemini model
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

            print("\nRAW GEMINI RESPONSE:")
            print(raw.decode())

            result = json.loads(raw)
    except urllib.error.HTTPError as e:
        if e.code == 429:
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
            except:
                pass

            text = text[: text.rfind("SCORE:")].strip()
            break

    return text, score


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_summary():
    settings = load_settings()

    api_key = settings.get(
        "gemini_api_key",
        ""
    ).strip()

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not set. Add it in Settings."
        )

    # Read activity log
    from pathlib import Path

    log_file = (
        Path(__file__).parents[2]
        / "scraper"
        / "data"
        / "daily_log.json"
    )

    activity_log = []

    if log_file.exists():
        try:
            activity_log = json.loads(
                log_file.read_text()
            )

        except Exception as e:
            print("\nFAILED TO LOAD ACTIVITY LOG")
            print(str(e))

    summary_text, score = _call_gemini(
        _build_prompt(activity_log),
        api_key
    )

    _latest_summary["summary"] = summary_text
    _latest_summary["score"] = score
    _latest_summary["generated_at"] = (
        datetime.now().isoformat()
    )

    return dict(_latest_summary)


@router.get("/latest")
async def get_latest_summary():
    return dict(_latest_summary)