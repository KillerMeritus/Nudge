"""
Tasks router — full CRUD backed by tasks.json via task_store.
"""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.storage.task_store import load_tasks, save_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = ""
    estimated_hours: int = 0
    estimated_minutes: int = Field(default=0, ge=0, le=59)
    priority: str = "Medium"          # "Low" | "Medium" | "High"
    tags: list[str] = []
    status: str = "Todo"              # "Todo" | "In Progress" | "Done"
    is_recurring: bool = False


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    estimated_hours: Optional[int] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0, le=59)
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    is_recurring: Optional[bool] = None


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.get("")
async def get_tasks():
    return load_tasks()


@router.post("", status_code=201)
async def create_task(body: TaskCreate):
    tasks = load_tasks()
    new_task = {
        "id": str(uuid.uuid4()),
        **body.model_dump(),
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    tasks.append(new_task)
    save_tasks(tasks)
    return new_task


@router.put("/{task_id}")
async def update_task(task_id: str, body: TaskUpdate):
    tasks = load_tasks()
    idx = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = body.model_dump(exclude_none=True)
    task = tasks[idx]
    task.update(updates)

    # Set completed_at when status flips to Done
    if updates.get("status") == "Done" and task.get("completed_at") is None:
        task["completed_at"] = datetime.now().isoformat()
    elif updates.get("status") != "Done":
        task["completed_at"] = None

    tasks[idx] = task
    save_tasks(tasks)
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    tasks = load_tasks()
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        raise HTTPException(status_code=404, detail="Task not found")
    save_tasks(new_tasks)
    return {"deleted": True}
