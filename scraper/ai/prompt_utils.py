"""
prompt_utils.py — BE-2 / ai
Shared prompt builder and response parser used by both ollama_client and gemini_client.
Centralised here so both backends stay in sync on format changes.
"""

import re
from datetime import date


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(daily_log: list[dict], task_list: list[dict] | None = None) -> str:
    """
    Build a structured productivity-summary prompt from the daily activity log.

    Compresses consecutive same-app entries to keep the prompt token-efficient.
    Returns a plain string ready to be sent to any LLM backend.
    """
    today = date.today().strftime("%B %d, %Y")

    # Compress log: group consecutive entries with the same app_name
    compressed: list[dict] = []
    for entry in daily_log:
        if compressed and compressed[-1]["app_name"] == entry.get("app_name"):
            compressed[-1]["count"] = compressed[-1].get("count", 1) + 1
            compressed[-1]["last_window"] = entry.get("window_title", "")
        else:
            compressed.append({
                "app_name": entry.get("app_name", "Unknown"),
                "last_window": entry.get("window_title", ""),
                "count": 1,
                "timestamp": entry.get("timestamp", ""),
            })

    activity_lines = []
    for item in compressed:
        count_str = f" (×{item['count']})" if item["count"] > 1 else ""
        activity_lines.append(f"  - {item['app_name']}{count_str}: {item['last_window']}")

    activity_block = (
        "\n".join(activity_lines) if activity_lines else "  (no activity recorded)"
    )

    task_block = ""
    if task_list:
        task_lines = [
            f"  - [{t.get('status', '?')}] {t.get('title', 'Untitled')} "
            f"(Priority: {t.get('priority', '?')})"
            for t in task_list
        ]
        task_block = "\nYour tasks for today:\n" + "\n".join(task_lines)

    return f"""You are a productivity assistant analyzing a user's computer activity for {today}.

Activity log (chronological, app switches):
{activity_block}
{task_block}

Please provide a structured productivity summary with EXACTLY this format:
---
SUMMARY: <2-3 sentence overview of how the user spent their time>
SCORE: <a number from 1.0 to 10.0 representing overall focus and productivity>
FOCUS_AREAS: <bullet list of main activities>
DISTRACTIONS: <bullet list of time-wasting or off-task activities, if any>
RECOMMENDATION: <one actionable suggestion for the rest of the day>
---

Be concise. Do not add any text outside the --- delimiters."""


# ─────────────────────────────────────────────────────────────────────────────
# Response parser  (shared — works for Gemma/Ollama and Gemini output)
# ─────────────────────────────────────────────────────────────────────────────

def parse_response(raw: str) -> dict:
    """
    Parses an LLM plain-text response into a structured dict.
    Handles both the ideal --- delimited format and looser output gracefully.

    Returns:
        {
            "summary": str,
            "score": float,
            "focus_areas": list[str],
            "distractions": list[str],
            "recommendation": str,
        }
    """
    result: dict = {
        "summary": "",
        "score": 5.0,
        "focus_areas": [],
        "distractions": [],
        "recommendation": "",
    }

    # Try to extract between --- delimiters first
    block_match = re.search(r"---\s*(.*?)\s*---", raw, re.DOTALL)
    content = block_match.group(1) if block_match else raw

    last_section = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("SUMMARY:"):
            result["summary"] = stripped[len("SUMMARY:"):].strip()
            last_section = "summary"
        elif stripped.startswith("SCORE:"):
            m = re.search(r"[\d.]+", stripped)
            if m:
                try:
                    result["score"] = float(m.group())
                except ValueError:
                    pass
            last_section = "score"
        elif stripped.startswith("FOCUS_AREAS:"):
            inline = stripped[len("FOCUS_AREAS:"):].strip()
            if inline:
                result["focus_areas"].append(inline)
            last_section = "focus"
        elif stripped.startswith("DISTRACTIONS:"):
            inline = stripped[len("DISTRACTIONS:"):].strip()
            if inline:
                result["distractions"].append(inline)
            last_section = "distractions"
        elif stripped.startswith("RECOMMENDATION:"):
            result["recommendation"] = stripped[len("RECOMMENDATION:"):].strip()
            last_section = "recommendation"
        elif stripped.startswith("- "):
            # Continuation bullet under the previous section
            bullet = stripped[2:]
            if last_section == "focus":
                result["focus_areas"].append(bullet)
            elif last_section == "distractions":
                result["distractions"].append(bullet)
        elif last_section == "summary" and result["summary"]:
            # Multi-sentence SUMMARY continuation
            result["summary"] += " " + stripped
        elif last_section == "recommendation" and result["recommendation"]:
            result["recommendation"] += " " + stripped

    return result
