from tools.tool import Tool
import threading
from agent_context import AgentContext
from tools.tool_message_bus import message_bus

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
    # Lazy import to avoid circular import via agent_profile/tool registry.
    from agent_factory import create_agent

    if message_bus.is_online(name):
        return f"Error: '{name}' is already online"

    # Pre-register so the agent is immediately reachable via send_message
    message_bus.register(name, role)

    agent = create_agent(
        name=name,
        role=role,
        profile="spawned",
    )

    thread = threading.Thread(
        target=agent.run_loop,
        args=(),
        daemon=True,
    )

    thread.start()
    return f"Spawned '{name}' (role: {role}). It is now online and reachable via send_message."


spawn_tool_instance = Tool(name=NAME, content=spawn_tool, function=spawn)
