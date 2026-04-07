from config import WORKDIR
from tool_bash import bash_tool_instance
from tool_write_file import write_file_tool_instance
from tool_read_file import read_file_tool_instance
from tool_edit_file import edit_file_tool_instance
from tool_members import members_tool_instance
from tool_message_bus import send_message_tool_instance
from tool_compact import compact_tool_instance
from tool_skill import skill, skill_tool_instance

BASE_TOOL_REGISTRY = {
    "bash": bash_tool_instance,
    "write_file": write_file_tool_instance,
    "read_file": read_file_tool_instance,
    "edit_file": edit_file_tool_instance,
    "members": members_tool_instance,
    "send_message": send_message_tool_instance,
    "compact": compact_tool_instance,
    "get_skill": skill_tool_instance,
}

PROFILE_TOOL_NAMES = {
    "main": [
        "bash",
        "write_file",
        "sub_agent_task_tool",
        "read_file",
        "edit_file",
        "members",
        "spawn",
        "send_message",
        "compact",
        "get_skill",
    ],
    "spawned": [
        "bash",
        "write_file",
        "sub_agent_task_tool",
        "read_file",
        "edit_file",
        "members",
        "send_message",
        "compact",
        "get_skill",
    ],
    "delegated": [
        "bash",
        "write_file",
        "read_file",
        "edit_file",
        "get_skill",
    ],
}


def build_system_template(profile: str) -> str:
    skill_descriptions = skill.get_descriptions()

    if profile == "main":
        return f"""
Your name is {{name}} and your role is {{role}}.
You are the leader agent at {WORKDIR}.

Your primary job is to understand what the user wants and decide how to handle it:

1. If YOU can handle the request directly (coding, file ops, shell commands), do it yourself.
2. If a task is better suited for a specialist:
   a. Call `members` to see who is CURRENTLY ONLINE.
   b. If a suitable agent is online, use `send_message` to forward the task.
   c. If NO suitable agent is online, use `spawn` to create one first, THEN `send_message`.
3. IMPORTANT: `send_message` will FAIL if the recipient is offline. You MUST `spawn` first.
4. `members` only returns online agents — if it returns empty or no match, spawn what you need.
5. Always tell the user what you decided and why.

Use `members` to see who is online before routing.
Use `send_message` to talk to other agents (sender is auto-filled, just provide `to` and `content`).
Use `spawn` to create new specialist agents when needed.
Use `sub_agent_task_tool` for quick one-off subtasks that don't need a persistent agent.
Use `get_skill` to load specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill_descriptions}.
"""

    if profile == "spawned":
        return f"""
Your name is {{name}} and your role is {{role}}.
You are a persistent specialist agent running in your own thread at {WORKDIR}.

You were spawned by the leader (mainAgent) to handle a specific domain.
Messages arrive in your inbox automatically — just process them.
Use `send_message` to reply to mainAgent or talk to other online agents.
Use `members` to see who is currently online.
Use `sub_agent_task_tool` to delegate quick one-off subtasks.
Use `get_skill` to load specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill_descriptions}.
"""

    if profile == "delegated":
        return f"""
Your name is {{name}} and your role is {{role}}.
You are a temporary sub-agent created to handle a single task synchronously.
Your result will be returned directly to the caller — no message bus needed.
Focus on the task, produce a clear answer, then stop.
Use `get_skill` to load specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill_descriptions}.
"""

    raise ValueError(f"Unknown profile '{profile}'")


def build_tool_box(profile: str, extra_registry: dict | None = None):
    if profile not in PROFILE_TOOL_NAMES:
        raise ValueError(f"Unknown profile '{profile}'")

    registry = dict(BASE_TOOL_REGISTRY)
    if extra_registry:
        registry.update(extra_registry)

    tools = []
    for tool_name in PROFILE_TOOL_NAMES[profile]:
        tool_instance = registry.get(tool_name)
        if tool_instance is None:
            raise ValueError(
                f"Tool '{tool_name}' required by profile '{profile}' is not registered"
            )
        tools.append(tool_instance)
    return tools
