import json
from tool import Tool
from agent_context import AgentContext
from team_state import list_online_agents

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
    agents = list_online_agents()
    if not agents:
        return "No agents are online."
    return json.dumps(agents, ensure_ascii=False)


members_tool_instance = Tool(name=NAME, content=members_tool, function=member_names)
