from tool import Tool
from agent_context import AgentContext
from agent_factory import create_agent

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


def sub_agent_task(agent_context: AgentContext, prompt: str) -> str:
    subAgent = create_agent(
        name="subAgent",
        role="assistant",
        profile="delegated",
    )

    subAgent.context.messages.append({"role": "user", "content": prompt})
    subAgent.one_task()
    return subAgent.context.messages[-1]["content"] if subAgent.context.messages else ""


sub_agent_task_tool_instance = Tool(
    name=NAME, content=sub_agent_task_tool, function=sub_agent_task
)
