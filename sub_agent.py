import os
from client import client
from log import log_message, log_input
from todo_manager import tm, todo_manager_tool
import os
import json

WORKING_DIR = os.getcwd()

SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKING_DIR}. Complete the given task, then summarize your findings."

SUB_AGENT_TOOLS = [
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


def run_sub_tool(name: str, args: dict) -> str:
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


def sub_agent(prompt: str) -> str:
    sub_messages = [
        {"role": "system", "content": SUBAGENT_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    while True:
        log_input(sub_messages)
        response = client.chat.completions.create(
            model="doubao-seed-2-0-lite-260215",
            messages=sub_messages,
            tools=SUB_AGENT_TOOLS,
            max_tokens=8000,
            n=1,
        )
        choice = response.choices[0]
        msg = choice.message
        log_message(msg)

        # append the assistant message to the conversation, including any tool calls or refusals
        sub_messages.append({"role": msg.role, "content": msg.content})

        if choice.finish_reason != "tool_calls":
            break

        # need to run the tool calls and append the results to the conversation before the next turn
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = run_sub_tool(tc.function.name, args)
            sub_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return sub_messages[-1]["content"]
