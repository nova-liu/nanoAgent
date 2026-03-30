import subprocess, os
from todomanager import todo_manager_tool, tm

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a bash command.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read content from a file.",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "old_content": {"type": "string"},
                    "new_content": {"type": "string"},
                },
                "required": ["filename", "old_content", "new_content"],
            },
        },
    },
    todo_manager_tool,
]


def run_tool(name: str, args: dict) -> str:
    if name == "bash":
        return run_bash(args["command"])
    elif name == "read_file":
        return read_file(args["filename"])
    elif name == "write_file":
        return write_file(args["filename"], args["content"])
    elif name == "edit_file":
        return edit_file(args["filename"], args["old_content"], args["new_content"])
    elif name == "todo_manager":
        return tm.update(args["items"])
    return f"unknown tool: {name}"


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def read_file(filename: str) -> str:
    if not os.path.isfile(filename):
        return f"Error: File '{filename}' does not exist."
    try:
        with open(filename, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{filename}': {str(e)}"


def write_file(filename: str, content: str) -> str:
    try:
        with open(filename, "w") as f:
            f.write(content)
        return f"File '{filename}' written successfully."
    except Exception as e:
        return f"Error writing file '{filename}': {str(e)}"


def edit_file(filename: str, old_content: str, new_content: str) -> str:
    if not os.path.isfile(filename):
        return f"Error: File '{filename}' does not exist."
    try:
        with open(filename, "r") as f:
            content = f.read()
        if old_content not in content:
            return f"Error: Old content not found in '{filename}'."
        updated_content = content.replace(old_content, new_content)
        with open(filename, "w") as f:
            f.write(updated_content)
        return f"File '{filename}' edited successfully."
    except Exception as e:
        return f"Error editing file '{filename}': {str(e)}"
