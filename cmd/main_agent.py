from config import WORKDIR
from agent import Agent
from tool_skill import skill, skill_tool_instance
from client import client
import threading

from tool_bash import bash_tool_instance
from tool_write_file import write_file_tool_instance
from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_read_file import read_file_tool_instance
from tool_edit_file import edit_file_tool_instance
from tool_members import members_tool_instance
from tool_spawn import spawn_tool_instance
from tool_message_bus import send_message_tool_instance, read_inbox_tool_instance, message_bus
from tool_compact import compact_tool_instance

SYSTEM_TEMPLATE = f"""
Your name is {{name}} and your role is {{role}}.
You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
Use the sub_agent_task_tool to delegate exploration or subtasks.
"""

DEFAULT_TOOL_BOX = [
    bash_tool_instance,
    write_file_tool_instance,
    sub_agent_task_tool_instance,
    read_file_tool_instance,
    edit_file_tool_instance,
    members_tool_instance,
    spawn_tool_instance,
    send_message_tool_instance,
    read_inbox_tool_instance,
    compact_tool_instance,
    skill_tool_instance,
]

mainAgent = Agent(
    tools=DEFAULT_TOOL_BOX,
    client=client,
    name="mainAgent",
    role="leader",
    system_template=SYSTEM_TEMPLATE,
)


if __name__ == "__main__":
    thread = threading.Thread(
        target=mainAgent.run_loop,
        args=(),
        daemon=True,
    )
    thread.start()
    print(f"\033[93m[System]: 欢迎进入多 Agent 流式聊天室！输入 'quit' 或 'exit' 退出。")
    print("-" * 60)

    while True:
        try:
            # 用户输入阶段：此时后台没有 Agent 在运行，保证输入框干净
            user_input = input(
                f"\033[93m[User]: "
            )

            if user_input.strip().lower() in ["quit", "exit"]:
                print("-" * 60)
                break

            if not user_input.strip():
                continue
            message_bus.send(None, "user", "mainAgent", user_input)
            # 触发 Agent 处理阶段

        except KeyboardInterrupt:
            print()
            print("-" * 60)
            print(f"\033[93m[System]: 检测到中断，退出聊天室。")
            break
        except Exception as e:
            print("-" * 60)
            print(f"\033[93m[System]: 发生错误: {e}")
