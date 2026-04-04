from tool import Tool
from agent_context import AgentContext
from agent import Agent
from client import client

from tool_skill import skill, skill_tool_instance

from tool_bash import bash_tool_instance
from tool_write_file import write_file_tool_instance
from tool_read_file import read_file_tool_instance
from tool_edit_file import edit_file_tool_instance
from tool_members import members_tool_instance
from tool_message_bus import send_message_tool_instance, read_inbox_tool_instance

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

SUB_AGENT_SYSTEM_TEMPLATE = f"""
Your name is {{name}} and your role is {{role}}.
You are a sub-agent created by the main agent to assist with specific tasks.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
You can't spawn new agents, and you don't have access to the sub_agent_task_tool. Focus on the task given by the main agent and report back the results.
"""

SUB_AGENT_TOOL_BOX = [
    bash_tool_instance,
    write_file_tool_instance,
    read_file_tool_instance,
    edit_file_tool_instance,
    members_tool_instance,
    send_message_tool_instance,
    read_inbox_tool_instance,
    skill_tool_instance,
]


def sub_agent_task(agent_context: AgentContext, prompt: str) -> str:
    subAgent = Agent(
        system_template=SUB_AGENT_SYSTEM_TEMPLATE,
        tools=SUB_AGENT_TOOL_BOX,
        client=client,
        name="subAgent",
        role="assistant",
    )

    subAgent.context.messages.append({"role": "user", "content": prompt})
    subAgent.one_task()
    return subAgent.context.messages[-1]["content"] if subAgent.context.messages else ""


sub_agent_task_tool_instance = Tool(
    name=NAME, content=sub_agent_task_tool, function=sub_agent_task
)
