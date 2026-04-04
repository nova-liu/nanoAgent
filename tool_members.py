from config import TEAM_CONFIG
from tool import Tool
from agent_context import AgentContext

NAME = "members"
members_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "List all teammates with their roles and statuses.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "required": [],
    },
}


def member_names(agent_context: AgentContext) -> str:
    return ", ".join([m["name"] for m in TEAM_CONFIG["members"]])


members_tool_instance = Tool(name=NAME, content=members_tool, function=member_names)
