import json
from tool import Tool
from agent_context import AgentContext
from tool_message_bus import message_bus

NAME = "members"
members_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "List all ONLINE teammates with their roles. Only shows agents that are currently running and reachable.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "required": [],
    },
}


def member_names(agent_context: AgentContext) -> str:
    agents = message_bus.list_agents()
    if not agents:
        return "No agents are online."
    return json.dumps(agents, ensure_ascii=False)


members_tool_instance = Tool(name=NAME, content=members_tool, function=member_names)
