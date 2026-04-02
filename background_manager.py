import threading
import subprocess
import uuid
import os

WORKDIR = os.getcwd()

# -- BackgroundManager: threaded execution + notification queue --
class BackgroundManager:
    def __init__(self, workdir=WORKDIR):
        self.tasks = {}  # task_id -> {status, result, command}
        self._notification_queue = []  # completed task results
        self._lock = threading.Lock()
        self.workdir = workdir

    def run(self, command: str) -> str:
        """Start a background thread, return task_id immediately."""
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {"status": "running", "result": None, "command": command}
        thread = threading.Thread(
            target=self._execute, args=(task_id, command), daemon=True
        )
        thread.start()
        return f"Background task {task_id} started: {command[:80]}"

    def _execute(self, task_id: str, command: str):
        """Thread target: run subprocess, capture output, push to queue."""
        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = (r.stdout + r.stderr).strip()[:50000]
            status = "completed"
        except subprocess.TimeoutExpired:
            output = "Error: Timeout (300s)"
            status = "timeout"
        except Exception as e:
            output = f"Error: {e}"
            status = "error"
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["result"] = output or "(no output)"
        with self._lock:
            self._notification_queue.append(
                {
                    "task_id": task_id,
                    "status": status,
                    "command": command[:80],
                    "result": (output or "(no output)")[:500],
                }
            )

    def check(self, task_id: str = None) -> str:
        """Check status of one task or list all."""
        if task_id:
            t = self.tasks.get(task_id)
            if not t:
                return f"Error: Unknown task {task_id}"
            return (
                f"[{t['status']}] {t['command'][:60]}\n{t.get('result') or '(running)'}"
            )
        lines = []
        for tid, t in self.tasks.items():
            lines.append(f"{tid}: [{t['status']}] {t['command'][:60]}")
        return "\n".join(lines) if lines else "No background tasks."

    def drain_notifications(self) -> list:
        """Return and clear all pending completion notifications."""
        with self._lock:
            notifs = list(self._notification_queue)
            self._notification_queue.clear()
        return notifs


BG = BackgroundManager()

background_run_tool = {
    "type": "function",
    "function": {
        "name": "background_run",
        "description": "Run a command in the background. Use 'check' to get status and result.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run."},
            },
            "required": ["command"],
        },
    },
}

check_background_tool = {
    "type": "function",
    "function": {
        "name": "check_background",
        "description": "Check status of background tasks. Optionally provide a task_id to check a specific task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the task to check (optional).",
                },
            },
        },
    },
}
