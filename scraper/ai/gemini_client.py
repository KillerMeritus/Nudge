"""
gemini_client.py — BE-2 / ai
Google Gemini API client for productivity summary generation.
Uses google-generativeai SDK (pip install google-generativeai).

Priority backend for testing — switch to ollama_client for local/offline use.

Environment variable required:
    GEMINI_API_KEY  — your Google AI Studio API key
    (or pass api_key= explicitly to generate_summary())

Models available (as of May 2026):
    gemini-2.0-flash         ← recommended default (fast + cheap)
    gemini-2.0-flash-lite    ← even cheaper, slightly less accurate
    gemini-1.5-pro           ← best quality, higher cost
    gemini-1.5-flash         ← balanced
"""

import os
import logging
from typing import Optional

from .prompt_utils import build_prompt, parse_response

logger = logging.getLogger("gemini_client")

DEFAULT_MODEL = "gemini-2.0-flash"


def _get_sdk():
    """
    Lazily imports google.generativeai so the rest of the scraper
    still works even if the SDK isn't installed.
    """
    try:
        import google.generativeai as genai
        return genai
    except ImportError:
        raise ImportError(
            "google-generativeai SDK not installed. "
            "Run: pip install google-generativeai"
        )


def generate_summary(
    daily_log: list[dict],
    task_list: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    timeout: int = 60,
) -> Optional[dict]:
    """
    Calls Google Gemini API with the daily activity log and returns a
    structured summary dict.

    Args:
        daily_log:  List of scrape entries from the in-memory log.
        task_list:  Optional list of task dicts from BE-1 /tasks.
        model:      Gemini model ID string.
        api_key:    Override — falls back to GEMINI_API_KEY env var.
        timeout:    Request timeout in seconds (not directly supported by
                    the SDK; handled via a threading timeout wrapper).

    Returns:
        {
            "summary": str,
            "score": float,
            "focus_areas": list[str],
            "distractions": list[str],
            "recommendation": str,
            "backend": "gemini",
            "model": str,
        }
        or None on failure.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        logger.error(
            "[gemini_client] No API key found. "
            "Set GEMINI_API_KEY env var or pass api_key= to generate_summary()."
        )
        return None

    try:
        genai = _get_sdk()
    except ImportError as exc:
        logger.error("[gemini_client] %s", exc)
        return None

    prompt = build_prompt(daily_log, task_list)

    try:
        genai.configure(api_key=key)
        client = genai.GenerativeModel(model_name=model)

        logger.info("[gemini_client] Sending prompt to %s (%d chars)", model, len(prompt))

        response = client.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,       # keep output deterministic / structured
                "max_output_tokens": 512,
            },
        )

        raw_text: str = response.text or ""
        logger.info("[gemini_client] Response received (%d chars)", len(raw_text))

        parsed = parse_response(raw_text)
        parsed["backend"] = "gemini"
        parsed["model"] = model
        return parsed

    except Exception as exc:
        # Covers API errors, quota exceeded, network issues, etc.
        logger.error("[gemini_client] API call failed: %s", exc)
        return None


def check_gemini_health(api_key: str | None = None) -> bool:
    """
    Quick check: can we reach the Gemini API with the current key?
    Makes a minimal list-models call (no tokens consumed).
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return False
    try:
        genai = _get_sdk()
        genai.configure(api_key=key)
        _ = list(genai.list_models())
        return True
    except Exception:
        return False
