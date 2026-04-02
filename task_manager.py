import json
from config import TASKS_DIR
from pathlib import Path


class TaskManager:
    def __init__(self, task_dir: Path = TASKS_DIR):
        self.dir = task_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def _max_id(self):
        ids = [int(f.stem.split("_")[1]) for f in self.dir.glob("task_*.json")]
        return max(ids) if ids else 0

    def _load(self, task_id: int) -> dict:
        path = self.dir / f"task_{task_id}.json"
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        return json.loads(path.read_text())

    def _save(self, task: dict):
        path = self.dir / f"task_{task['id']}.json"
        path.write_text(json.dumps(task, indent=2))

    def create(self, subject: str, description: str) -> str:
        task = {
            "id": self._next_id,
            "subject": subject,
            "description": description,
            "status": "pending",
            "blockedBy": [],
            "blocks": [],
            "owner": "",
        }
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2)

    def get(self, task_id: int) -> str:
        return json.dumps(self._load(task_id), indent=2)

    def update(
        self,
        task_id: int,
        status: str = None,
        add_blocked_by: list = None,
        add_blocks: list = None,
    ) -> str:
        task = self._load(task_id)
        if status:
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Invalid status: {status}")
            task["status"] = status
            # When a task is completed, remove it from all other tasks' blockedBy
            if status == "completed":
                self._clear_dependency(task_id)
        if add_blocked_by:
            task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
        if add_blocks:
            task["blocks"] = list(set(task["blocks"] + add_blocks))
            # Bidirectional: also update the blocked tasks' blockedBy lists
            for blocked_id in add_blocks:
                try:
                    blocked = self._load(blocked_id)
                    if task_id not in blocked["blockedBy"]:
                        blocked["blockedBy"].append(task_id)
                        self._save(blocked)
                except ValueError:
                    pass
        self._save(task)
        return json.dumps(task, indent=2)

    def _clear_dependency(self, completed_id: int):
        """Remove completed_id from all other tasks' blockedBy lists."""
        for f in self.dir.glob("task_*.json"):
            task = json.loads(f.read_text())
            if completed_id in task.get("blockedBy", []):
                task["blockedBy"].remove(completed_id)
                self._save(task)

    def list_all(self) -> str:
        tasks = []
        for f in sorted(self.dir.glob("task_*.json")):
            tasks.append(json.loads(f.read_text()))
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(
                t["status"], "[?]"
            )
            blocked = f" (blocked by: {t['blockedBy']})" if t.get("blockedBy") else ""
            lines.append(f"{marker} #{t['id']}: {t['subject']}{blocked}")
        return "\n".join(lines)


create_task_tool = {
    "type": "function",
    "function": {
        "name": "create_task",
        "description": "Create a new task with a subject and description.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Task subject"},
                "description": {
                    "type": "string",
                    "description": "Task description",
                },
            },
            "required": ["subject", "description"],
        },
    },
}

get_task_tool = {
    "type": "function",
    "function": {
        "name": "get_task",
        "description": "Get details of a task by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Task ID"},
            },
            "required": ["id"],
        },
    },
}

update_task_tool = {
    "type": "function",
    "function": {
        "name": "update_task",
        "description": "Update a task's status or dependencies.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Task ID"},
                "status": {
                    "type": "string",
                    "description": "New status (pending, in_progress, completed)",
                },
                "add_blocked_by": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of task IDs that block this task",
                },
                "add_blocks": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of task IDs that this task blocks",
                },
            },
            "required": ["id"],
        },
    },
}

list_tasks_tool = {
    "type": "function",
    "function": {
        "name": "list_tasks",
        "description": "List all tasks with their status and dependencies.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

task_manager = TaskManager(TASKS_DIR)
