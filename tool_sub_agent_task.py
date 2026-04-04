from tool import Tool

NAME = "sub_agent_task_tool"

sub_agent_task_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Delegate a task to a sub-agent. The input is a prompt describing the task, and the output should be the final answer from the sub-agent after completing the task.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
            },
            "required": ["prompt"],
        },
    },
}


def sub_agent_task(prompt: str) -> str:
    return prompt


sub_agent_task_tool_instance = Tool(
    name=NAME, content=sub_agent_task_tool, function=sub_agent_task
)
