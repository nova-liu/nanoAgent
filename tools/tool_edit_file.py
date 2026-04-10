import os
from tools.tool import Tool
from agent_context import AgentContext

NAME = "edit_file"
edit_file_tool = {
    "type": "function",
    "function": {
        "name": NAME,
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


def edit_file(
    agent_context: AgentContext, filename: str, old_content: str, new_content: str
) -> str:
    if not os.path.isfile(filename):
        raise Exception(f"Error: File '{filename}' does not exist.")
    try:
        with open(filename, "r") as f:
            content = f.read()
        if old_content not in content:
            raise Exception(f"Error: Old content not found in '{filename}'.")
        updated_content = content.replace(old_content, new_content)
        with open(filename, "w") as f:
            f.write(updated_content)
        return f"File '{filename}' edited successfully."
    except Exception as e:
        raise Exception(f"Error editing file '{filename}': {str(e)}")


edit_file_tool_instance = Tool(name=NAME, content=edit_file_tool, function=edit_file)
