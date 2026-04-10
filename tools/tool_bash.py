import os
import subprocess
from tools.tool import Tool
from agent_context import AgentContext

NAME = "bash"
# tool bash
bash_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Run a bash command. Be cautious to avoid dangerous commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
        },
    },
}


def run_bash(agent_context: AgentContext, command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        raise Exception("Error: Dangerous command blocked")
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired as e:
        raise Exception(f"Error: Command timed out: {str(e)}")


bash_tool_instance = Tool(name=NAME, content=bash_tool, function=run_bash)
