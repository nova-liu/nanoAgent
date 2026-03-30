# item structer is:
# {   "id": "sequence id",
#     "text": "the content of the todo item",
#     "status": "pending" or "in_progress" or "completed"
# }


todo_manager_tool = {
    "type": "function",
    "function": {
        "name": "todo_manager",
        "description": "Manage todo items.",
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                    },
                },
                "required": ["id", "text", "status"],
            },
        },
    },
}


class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        if len(items) > 20:
            return "Error: Too many items. Maximum is 20."
        validated = []
        in_progress = []
        for i, item in enumerate(items):
            text = item.get("text", "").strip()
            status = item.get("status", "pending").lower()
            id = item.get("id", str(i + 1))
        if not text:
            raise ValueError(f"Item {i + 1} is missing text.")
        if status not in ["pending", "in_progress", "completed"]:
            raise ValueError(f"Item {i + 1} has invalid status: {status}")
        if status == "in_progress":
            in_progress.append(id)
        validated.append({"id": id, "text": text, "status": status})
        if len(in_progress) > 1:
            raise ValueError(
                f"Only one item can be in_progress, but found: {in_progress}"
            )
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todo items."
        lines = []
        for item in self.items:
            status_icon = {"pending": "🕒", "in_progress": "⏳", "completed": "✅"}.get(
                item["status"], ""
            )
            lines.append(f"{status_icon} [{item['id']}] {item['text']}")
        return "\n".join(lines)


tm = TodoManager()
