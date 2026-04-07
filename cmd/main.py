import threading
import sys

from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_spawn import spawn_tool_instance
from tool_message_bus import message_bus
from agent_factory import create_agent

# ── colours ──
DIM = "\033[2m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

mainAgent = create_agent(
    name="mainAgent",
    role="leader",
    profile="main",
    extra_registry={
        "sub_agent_task_tool": sub_agent_task_tool_instance,
        "spawn": spawn_tool_instance,
    },
)


# ── status bar ──
def render_status_bar():
    agents = message_bus.list_agents()

    parts = []
    for a in agents:
        parts.append(f"{GREEN}●{RESET} {a['name']}({a['role']})")

    bar = "  ".join(parts) if parts else f"{DIM}(no agents){RESET}"
    sys.stdout.write(f"{DIM}─── agents: {bar} {DIM}───{RESET}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    # Pre-register mainAgent queue so user messages arrive before run_loop starts
    message_bus.register("mainAgent", "leader")

    import agent as _agent_mod

    _agent_mod.on_agent_output_done = render_status_bar

    thread = threading.Thread(
        target=mainAgent.run_loop,
        args=(),
        daemon=True,
    )
    thread.start()

    print(f"{YELLOW}nanoAgent 聊天室{RESET}")
    print(f"{DIM}直接输入文字和 leader 对话，leader 会自动路由给合适的 agent。{RESET}")
    print(f"{DIM}输入 quit 或 exit 退出。{RESET}")
    print()

    while True:
        try:
            render_status_bar()
            user_input = input(f"{CYAN}> {RESET}")

            if user_input.strip().lower() in ["quit", "exit"]:
                break

            if not user_input.strip():
                continue

            message_bus.send(None, to="mainAgent", content=user_input)

        except KeyboardInterrupt:
            print()
            break
        except Exception as e:
            print(f"{YELLOW}[error]: {e}{RESET}")
