from tool import Tool
import threading
from tool_sub_agent_task import sub_agent_task_tool_instance
from agent_context import AgentContext
from agent_factory import create_agent
from team_state import is_online, touch_heartbeat

NAME = "spawn"

spawn_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Spawn a new agent with a given name and role. The agent starts immediately and becomes reachable via send_message.",
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
    if is_online(name):
        return f"Error: '{name}' is already online"

    touch_heartbeat(name=name, role=role)

    agent = create_agent(
        name=name,
        role=role,
        profile="spawned",
        extra_registry={
            "sub_agent_task_tool": sub_agent_task_tool_instance,
        },
    )

    thread = threading.Thread(
        target=agent.run_loop,
        args=(),
        daemon=True,
    )

    thread.start()
    return f"Spawned '{name}' (role: {role}). It is now online and reachable via send_message."


spawn_tool_instance = Tool(name=NAME, content=spawn_tool, function=spawn)
