from agent import Agent
from tool import Tool
from config import TEAM_CONFIG, TEAM_CONFIG_PATH
import threading
import json
from client import client
from tool_skill import skill, skill_tool_instance
from tool_bash import bash_tool_instance
from tool_write_file import write_file_tool_instance
from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_read_file import read_file_tool_instance
from tool_edit_file import edit_file_tool_instance
from tool_members import members_tool_instance
from tool_message_bus import send_message_tool_instance, read_inbox_tool_instance
from tool_compact import compact_tool_instance
from agent_context import AgentContext

NAME = "spawn"

spawn_tool = {
    "type": "function",
    "function": {
        "name": NAME,
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

SPAWN_AGENT_SYSTEM_TEMPLATE = f"""
Your name is {{name}} and your role is {{role}}.
You are a sub-agent spawned by the main agent to assist with a specific task.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
Use the sub_agent_task_tool to delegate exploration or subtasks.
"""

SPAWN_SUB_AGENT_SYSTEM_TEMPLATE = f"""
Your name is {{name}} and your role is {{role}}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
"""

SPAWN_TOOL_BOX = [
    bash_tool_instance,
    write_file_tool_instance,
    sub_agent_task_tool_instance,
    read_file_tool_instance,
    edit_file_tool_instance,
    members_tool_instance,
    send_message_tool_instance,
    read_inbox_tool_instance,
    compact_tool_instance,
    skill_tool_instance,
]


def spawn(agent_context: AgentContext, name: str, role: str) -> str:
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

    mainAgent = Agent(
        tools=SPAWN_TOOL_BOX,
        client=client,
        name=name,
        role=role,
        system_template=SPAWN_AGENT_SYSTEM_TEMPLATE,
    )

    thread = threading.Thread(
        target=mainAgent.run_loop,
        args=(),
        daemon=True,
    )

    thread.start()
    return f"Spawned '{name}' (role: {role})"


spawn_tool_instance = Tool(name=NAME, content=spawn_tool, function=spawn)
