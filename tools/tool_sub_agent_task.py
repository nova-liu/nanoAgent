from tools.tool import Tool
from agent_context import AgentContext

NAME = "sub_agent_task_tool"

sub_agent_task_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": (
            "Delegate a quick, self-contained task to a temporary sub-agent. "
            "The sub-agent runs synchronously and returns its final answer. "
            "Use this for one-off tasks that don't need a persistent agent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Task description for the sub-agent",
                },
            },
            "required": ["prompt"],
        },
    },
}


def sub_agent_task(agent_context: AgentContext, prompt: str) -> str:
    # Lazy import to avoid circular import:
    # agent_factory -> agent_profile -> this module -> agent_factory
    from agent_factory import create_agent

    parent_name = (
        agent_context.name if agent_context and agent_context.name else "agent"
    )
    n = len(agent_context.messages) if agent_context else 0

    subAgent = create_agent(
        name=f"{parent_name}/sub_{n}",
        role=f"sub-agent of {parent_name}",
        profile="delegated",
    )

    subAgent.context.messages.append({"role": "user", "content": prompt})
    subAgent.one_task()
    return subAgent.context.messages[-1]["content"] if subAgent.context.messages else ""


sub_agent_task_tool_instance = Tool(
    name=NAME, content=sub_agent_task_tool, function=sub_agent_task
)
