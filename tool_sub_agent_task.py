from tool import Tool
from agent_context import AgentContext
from agent_factory import create_agent
import threading

NAME = "sub_agent_task_tool"

_sub_counter_lock = threading.Lock()
_sub_counters: dict[str, int] = {}

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


def _next_sub_name(parent: str) -> str:
    with _sub_counter_lock:
        n = _sub_counters.get(parent, 0) + 1
        _sub_counters[parent] = n
    return f"{parent}/sub_{n}"


def sub_agent_task(agent_context: AgentContext, prompt: str) -> str:
    parent_name = agent_context.name if agent_context else "unknown"
    sub_name = _next_sub_name(parent_name)

    subAgent = create_agent(
        name=sub_name,
        role=f"sub-agent of {parent_name}",
        profile="delegated",
    )

    subAgent.context.messages.append({"role": "user", "content": prompt})
    subAgent.one_task()
    return subAgent.context.messages[-1]["content"] if subAgent.context.messages else ""


sub_agent_task_tool_instance = Tool(
    name=NAME, content=sub_agent_task_tool, function=sub_agent_task
)
