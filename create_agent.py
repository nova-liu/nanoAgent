from t import Tool
from config import TEAM_CONFIG, TEAM_CONFIG_PATH, WORKDIR
from agent import Agent
from client import client
from skill import skill, skill_tool
from todo_manager import todo_manager, todo_manager_tool
from task_manager import (
    task_manager,
    create_task_tool,
    get_task_tool,
    update_task_tool,
    list_tasks_tool,
)
from background_manager import (
    background_manager,
    background_run_tool,
    check_background_tool,
)
from utils import compact, run_bash, read_file, write_file, edit_file
from message_bus import message_bus, send_message_tool, read_inbox_tool
from background_manager import background_manager
import threading, json, subprocess, os

SYSTEM_TEMPLATE = f"""
Your name is {{name}} and your role is {{role}}.
You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
Use the task tool to delegate exploration or subtasks.
"""

SUB_AGENT_SYSTEM_TEMPLATE = f"""
Your name is {{name}} and your role is {{role}}.
You are a sub-agent created by the main agent to assist with specific tasks.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
You can't spawn new agents, and you don't have access to the task tool. Focus on the task given by the main agent and report back the results.
"""


# tools
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

list_team_all_tool = {
    "type": "function",
    "function": {
        "name": "list_team_all",
        "description": "List all teammates with their roles and statuses.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "required": [],
    },
}

spawn_tool = {
    "type": "function",
    "function": {
        "name": "spawn",
        "description": "Spawn a new agent with a given name and role.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "role": {"type": "string"},
            },
            "required": ["name", "role"],
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


def member_names() -> str:
    return ", ".join([m["name"] for m in TEAM_CONFIG["members"]])


def spawn(name: str, role: str) -> str:
    member = None
    for m in TEAM_CONFIG["members"]:
        if m["name"] == name:
            member = m
    if member:
        if member["status"] not in ("idle", "shutdown"):
            return f"Error: '{name}' is currently {member['status']}"
        member["status"] = "working"
        member["role"] = role
    else:
        member = {"name": name, "role": role, "status": "working"}
        TEAM_CONFIG["members"].append(member)
    TEAM_CONFIG_PATH.write_text(json.dumps(TEAM_CONFIG, indent=2))

    subAgent = Agent(
        system_template=SUB_AGENT_SYSTEM_TEMPLATE,
        tools=tools,
        client=client,
        name="subAgent",
        role="assistant",
        message_bus=message_bus,
    )
    mainAgent = Agent(
        tools=tools,
        client=client,
        sub_agent=subAgent,
        name="mainAgent",
        role="leader",
        message_bus=message_bus,
    )

    thread = threading.Thread(
        target=mainAgent.run_loop,
        args=(),
        daemon=True,
    )

    mainAgent.threads[name] = thread
    thread.start()
    return f"Spawned '{name}' (role: {role})"


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


bash_tool_instance = Tool(name="bash", content=bash_tool, function=run_bash)

compact_tool_instance = Tool(name="compact", content=compact_tool, function=compact)

read_file_tool_instance = Tool(
    name="read_file", content=read_file_tool, function=read_file
)

write_file_tool_instance = Tool(
    name="write_file", content=write_file_tool, function=write_file
)

edit_file_tool_instance = Tool(
    name="edit_file", content=edit_file_tool, function=edit_file
)

sub_agent_tool_instance = Tool(
    name="sub_agent_tool", content=sub_agent_tool, function=sub_prompt
)

todo_tool = Tool(
    name="todo_manager", content=todo_manager_tool, function=todo_manager.update
)

skill_tool_instance = Tool(
    name="get_skill", content=skill_tool, function=skill.get_content
)

create_task_tool_instance = Tool(
    name="create_task", content=create_task_tool, function=task_manager.create
)

get_task_tool_instance = Tool(
    name="get_task", content=get_task_tool, function=task_manager.get
)

update_task_tool_instance = Tool(
    name="update_task", content=update_task_tool, function=task_manager.update
)

list_tasks_tool_instance = Tool(
    name="list_tasks", content=list_tasks_tool, function=task_manager.list_all
)

background_run_tool_instance = Tool(
    name="background_run", content=background_run_tool, function=background_manager.run
)

check_background_tool_instance = Tool(
    name="check_background",
    content=check_background_tool,
    function=background_manager.check,
)

send_message_tool_instance = Tool(
    name="send_message", content=send_message_tool, function=message_bus.send
)

read_inbox_tool_instance = Tool(
    name="read_inbox", content=read_inbox_tool, function=message_bus.read_inbox
)

list_team_all_tool_instance = Tool(
    name="list_team_all", content=list_team_all_tool, function=member_names
)

spawn_tool_instance = Tool(name="spawn", content=spawn_tool, function=spawn)

sub_agent_tool_instance = Tool(
    name="sub_agent_tool", content=sub_agent_tool, function=sub_prompt
)

tools = [
    bash_tool_instance,
    read_file_tool_instance,
    write_file_tool_instance,
    edit_file_tool_instance,
    todo_tool,
    sub_agent_tool_instance,
    skill_tool_instance,
    compact_tool_instance,
    create_task_tool_instance,
    get_task_tool_instance,
    update_task_tool_instance,
    list_tasks_tool_instance,
    background_run_tool_instance,
    check_background_tool_instance,
    list_team_all_tool_instance,
    spawn_tool_instance,
    send_message_tool_instance,
    read_inbox_tool_instance,
]


subAgent = Agent(
    system_template=SUB_AGENT_SYSTEM_TEMPLATE,
    tools=tools,
    client=client,
    name="subAgent",
    role="assistant",
    message_bus=message_bus,
)
mainAgent = Agent(
    tools=tools,
    client=client,
    sub_agent=subAgent,
    name="mainAgent",
    role="leader",
    message_bus=message_bus,
    system_template=SYSTEM_TEMPLATE,
)
