import subprocess, os
from todo_manager import todo_manager_tool, tm
from sub_agent import SUB_AGENT_TOOLS, sub_agent, run_sub_tool

TOOLS = SUB_AGENT_TOOLS + [
    {
        "type": "function",
        "function": {
            "name": "task_tool",
            "description": "Delegate a task to a sub-agent. The sub-agent will return a final answer, not intermediate thoughts.",
            "parameters": {
                "type": "object",
                "properties": {"prompt": {"type": "string"}},
                "required": ["prompt"],
            },
        },
    }
]


def run_tool(name, args):
    if name == "task_tool":
        return sub_agent(args["prompt"])
    return run_sub_tool(name, args)
