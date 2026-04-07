import threading

from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_spawn import spawn_tool_instance
from tool_message_bus import message_bus
from agent_factory import create_agent

mainAgent = create_agent(
    name="mainAgent",
    role="leader",
    profile="main",
    extra_registry={
        "sub_agent_task_tool": sub_agent_task_tool_instance,
        "spawn": spawn_tool_instance,
    },
)


if __name__ == "__main__":
    thread = threading.Thread(
        target=mainAgent.run_loop,
        args=(),
        daemon=True,
    )
    thread.start()
    print(
        f"\033[93m[System]: 欢迎进入多 Agent 流式聊天室！输入 'quit' 或 'exit' 退出。"
    )
    print("-" * 60)

    while True:
        try:
            # 用户输入阶段：此时后台没有 Agent 在运行，保证输入框干净
            user_input = input(f"\033[93m[User]: ")

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
