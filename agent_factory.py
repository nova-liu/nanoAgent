from agent import Agent
from client import client
from agent_profile import build_system_template, build_tool_box


def create_agent(
    *,
    name: str,
    role: str,
    profile: str,
    extra_registry: dict | None = None,
    model: str = "doubao-seed-2-0-mini-260215",
    max_tokens: int = 8000,
    max_context_tokens: int = 1600,
):
    return Agent(
        tools=build_tool_box(profile, extra_registry=extra_registry),
        client=client,
        name=name,
        role=role,
        system_template=build_system_template(profile),
        model=model,
        max_tokens=max_tokens,
        max_context_tokens=max_context_tokens,
    )
