"""
ollama_client.py — BE-2 / ai
HTTP client for the local Ollama API (Gemma model).
Sends the daily activity log as context and receives a structured summary.
"""

import requests
import logging
from typing import Optional

from .prompt_utils import build_prompt, parse_response

logger = logging.getLogger("ollama_client")

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:4b"


def generate_summary(
    daily_log: list[dict],
    task_list: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
) -> Optional[dict]:
    """
    Calls local Ollama /api/generate with the daily log.

    Returns a dict with keys: summary, score, focus_areas, distractions,
    recommendation, backend, model.
    Returns None on failure (Ollama not running, timeout, etc.)
    """
    prompt = build_prompt(daily_log, task_list)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        logger.info("[ollama_client] Sending prompt to %s (%d chars)", model, len(prompt))
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text: str = data.get("response", "")
        logger.info("[ollama_client] Response received (%d chars)", len(raw_text))
        parsed = parse_response(raw_text)
        parsed["backend"] = "ollama"
        parsed["model"] = model
        return parsed
    except requests.exceptions.ConnectionError:
        logger.warning("[ollama_client] Ollama not reachable at %s", OLLAMA_BASE_URL)
        return None
    except requests.exceptions.Timeout:
        logger.warning("[ollama_client] Request timed out after %ds", timeout)
        return None
    except Exception as exc:
        logger.error("[ollama_client] Unexpected error: %s", exc)
        return None


def check_ollama_health() -> bool:
    """Returns True if local Ollama API is reachable."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False
