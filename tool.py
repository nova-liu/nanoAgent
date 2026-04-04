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

from message_bus import send_message_tool, read_inbox_tool, message_bus

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
    list_team_all_tool,
    spawn_tool,
    send_message_tool,
    read_inbox_tool,
]





