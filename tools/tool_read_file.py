from tools.tool import Tool
import os
from agent_context import AgentContext

NAME = "read_file"

read_file_tool = {
    "type": "function",
    "function": {
        "name": NAME,
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


def read_file(agent_context: AgentContext, filename: str) -> str:
    if not os.path.isfile(filename):
        raise Exception(f"Error: File '{filename}' does not exist.")
    try:
        with open(filename, "r") as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Error reading file '{filename}': {str(e)}")


read_file_tool_instance = Tool(name=NAME, content=read_file_tool, function=read_file)
