"""
task_store.py — JSON-backed task persistence with file locking.
"""

import json
from pathlib import Path
from filelock import FileLock

TASKS_FILE = Path(__file__).parent.parent / "data" / "tasks.json"
LOCK_FILE  = Path(__file__).parent.parent / "data" / "tasks.json.lock"

# Ensure data directory exists
TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_tasks() -> list:
    with FileLock(str(LOCK_FILE)):
        if not TASKS_FILE.exists():
            return []
        try:
            return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []


def save_tasks(tasks: list) -> None:
    with FileLock(str(LOCK_FILE)):
        TASKS_FILE.write_text(
            json.dumps(tasks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
