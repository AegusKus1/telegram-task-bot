import json
import os
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join("data", "users.json")


def _ensure_db_exists() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_db() -> Dict[str, Any]:
    _ensure_db_exists()
    # utf-8-sig спокойно съедает BOM, если он вдруг появится
    with open(DB_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_db(db: Dict[str, Any]) -> None:
    _ensure_db_exists()
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_user(db: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"tasks": [], "done": []}
    return db[uid]


def add_task(user: Dict[str, Any], text: str, due_iso: str) -> None:
    # reminded: чтобы напоминание за день не отправлялось много раз
    user["tasks"].append({
        "text": text,
        "due": due_iso,       # YYYY-MM-DD
        "reminded": False
    })


def list_tasks(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    return user.get("tasks", [])


def complete_task(user: Dict[str, Any], index_1based: int) -> Dict[str, Any]:
    tasks = user.get("tasks", [])
    if index_1based < 1 or index_1based > len(tasks):
        raise IndexError("Task index out of range")
    task = tasks.pop(index_1based - 1)
    user.setdefault("done", []).append(task)
    return task


def get_stats(user: Dict[str, Any]) -> Dict[str, int]:
    in_progress = len(user.get("tasks", []))
    done = len(user.get("done", []))
    return {"in_progress": in_progress, "done": done}
