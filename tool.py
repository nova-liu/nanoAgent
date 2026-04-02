import subprocess, os
from todo_manager import todo_manager_tool, todo_manager
from skill import skill_tool, skill
from task_manager import (
    create_task_tool,
    get_task_tool,
    update_task_tool,
    list_tasks_tool,
    task_manager,
)
from background_manager import (
    background_run_tool,
    check_background_tool,
    background_manager,
)

sub_agent_tool = {
    "type": "function",
    "function": {
        "name": "sub_agent_tool",
        "description": "Delegate a task to a sub-agent. The input is a prompt describing the task, and the output should be the final answer from the sub-agent after completing the task.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
            },
            "required": ["prompt"],
        },
    },
}

compact_tool = {
    "type": "function",
    "function": {
        "name": "compact",
        "description": "Compact the conversation history to reduce token usage. This can be done by summarizing earlier messages or removing less relevant ones.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

bash_tool = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a bash command. Be cautious to avoid dangerous commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
        },
    },
}

write_file_tool = {
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
}

read_file_tool = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read content from a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
            },
            "required": ["filename"],
        },
    },
}

edit_file_tool = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Edit content of a file by replacing old content with new content.",
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
}


TOOLS = [
    bash_tool,
    read_file_tool,
    write_file_tool,
    edit_file_tool,
    todo_manager_tool,
    sub_agent_tool,
    skill_tool,
    compact_tool,
    create_task_tool,
    get_task_tool,
    update_task_tool,
    list_tasks_tool,
    background_run_tool,
    check_background_tool,
]

TOOL_HANDLERS = {t["function"]["name"]: t for t in TOOLS}


class Tool:
    def __init__(
        self,
        tools=TOOLS,
        background_manager=background_manager,
        todo_manager=todo_manager,
        task_manager=task_manager,
        skill=skill,
    ):
        self.tools = tools
        self.background_manager = background_manager
        self.todo_manager = todo_manager
        self.task_manager = task_manager
        self.skills = skill

    def dispatch(self, name, args) -> str:
        if name == "bash":
            return run_bash(args["command"])
        elif name == "read_file":
            return read_file(args["filename"])
        elif name == "write_file":
            return write_file(args["filename"], args["content"])
        elif name == "edit_file":
            return edit_file(args["filename"], args["old_content"], args["new_content"])
        elif name == "todo_manager":
            return self.todo_manager.update(args["items"])
        elif name == "sub_agent_tool":
            return sub_prompt(args["prompt"])
        elif name == "get_skill":
            return self.skills.get_content(args["name"])
        elif name == "compact":
            return compact()
        elif name == "create_task":
            return self.task_manager.create(args["subject"], args["description"])
        elif name == "get_task":
            return self.task_manager.get(args["id"])
        elif name == "update_task":
            return self.task_manager.update(
                args["id"],
                args.get("status"),
                args.get("add_blocked_by"),
                args.get("add_blocks"),
            )
        elif name == "list_tasks":
            return self.task_manager.list_all()
        elif name == "background_run":
            return self.background_manager.run(args["command"])
        elif name == "check_background":
            return self.background_manager.check(args.get("task_id"))
        else:
            raise Exception(f"Unknown tool: {name}")


tools = Tool()


def compact():
    # This is a placeholder for the actual compaction logic, which could involve summarizing or pruning messages.
    return "Conversation history compacted to reduce token usage."


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        raise Exception("Error: Dangerous command blocked")
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
    except subprocess.TimeoutExpired as e:
        raise Exception(f"Error: Command timed out: {str(e)}")


def read_file(filename: str) -> str:
    if not os.path.isfile(filename):
        raise Exception(f"Error: File '{filename}' does not exist.")
    try:
        with open(filename, "r") as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Error reading file '{filename}': {str(e)}")


def write_file(filename: str, content: str) -> str:
    try:
        with open(filename, "w") as f:
            f.write(content)
        return f"File '{filename}' written successfully."
    except Exception as e:
        raise Exception(f"Error writing file '{filename}': {str(e)}")


def edit_file(filename: str, old_content: str, new_content: str) -> str:
    if not os.path.isfile(filename):
        raise Exception(f"Error: File '{filename}' does not exist.")
    try:
        with open(filename, "r") as f:
            content = f.read()
        if old_content not in content:
            raise Exception(f"Error: Old content not found in '{filename}'.")
        updated_content = content.replace(old_content, new_content)
        with open(filename, "w") as f:
            f.write(updated_content)
        return f"File '{filename}' edited successfully."
    except Exception as e:
        raise Exception(f"Error editing file '{filename}': {str(e)}")


def sub_prompt(prompt: str) -> str:
    return prompt
