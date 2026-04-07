from config import WORKDIR
from tool_bash import bash_tool_instance
from tool_write_file import write_file_tool_instance
from tool_read_file import read_file_tool_instance
from tool_edit_file import edit_file_tool_instance
from tool_members import members_tool_instance
from tool_message_bus import send_message_tool_instance, read_inbox_tool_instance
from tool_compact import compact_tool_instance
from tool_skill import skill, skill_tool_instance

BASE_TOOL_REGISTRY = {
    "bash": bash_tool_instance,
    "write_file": write_file_tool_instance,
    "read_file": read_file_tool_instance,
    "edit_file": edit_file_tool_instance,
    "members": members_tool_instance,
    "send_message": send_message_tool_instance,
    "read_inbox": read_inbox_tool_instance,
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
        "read_inbox",
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
        "read_inbox",
        "compact",
        "get_skill",
    ],
    "delegated": [
        "bash",
        "write_file",
        "read_file",
        "edit_file",
        "members",
        "send_message",
        "read_inbox",
        "get_skill",
    ],
}


def build_system_template(profile: str) -> str:
    skill_descriptions = skill.get_descriptions()

    if profile == "main":
        return f"""
Your name is {{name}} and your role is {{role}}.
You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill_descriptions}.
Use the sub_agent_task_tool to delegate exploration or subtasks.
"""

    if profile == "spawned":
        return f"""
Your name is {{name}} and your role is {{role}}.
You are a sub-agent spawned by the main agent to assist with a specific task.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill_descriptions}.
Use the sub_agent_task_tool to delegate exploration or subtasks.
"""

    if profile == "delegated":
        return f"""
Your name is {{name}} and your role is {{role}}.
You are a sub-agent created by the main agent to assist with specific tasks.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill_descriptions}.
You can't spawn new agents, and you don't have access to the sub_agent_task_tool. Focus on the task given by the main agent and report back the results.
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
