from tool import Tool
from config import TEAM_CONFIG, TEAM_CONFIG_PATH
import threading
import json
from tool_sub_agent_task import sub_agent_task_tool_instance
from agent_context import AgentContext
from agent_factory import create_agent

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

    mainAgent = create_agent(
        name=name,
        role=role,
        profile="spawned",
        extra_registry={
            "sub_agent_task_tool": sub_agent_task_tool_instance,
        },
    )

    thread = threading.Thread(
        target=mainAgent.run_loop,
        args=(),
        daemon=True,
    )

    thread.start()
    return f"Spawned '{name}' (role: {role})"


spawn_tool_instance = Tool(name=NAME, content=spawn_tool, function=spawn)
