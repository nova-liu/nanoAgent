import os
from tool import Tool

NAME = "write_file"

write_file_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Write content to a file. If the file already exists, it will be overwritten.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["filename", "content"],
        },
    },
}


def write_file(filename: str, content: str) -> str:
    try:
        with open(filename, "w") as f:
            f.write(content)
        return f"File '{filename}' written successfully."
    except Exception as e:
        raise Exception(f"Error writing file '{filename}': {str(e)}")


write_file_tool_instance = Tool(name=NAME, content=write_file_tool, function=write_file)
