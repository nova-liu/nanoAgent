from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_spawn import spawn_tool_instance
from tool_message_bus import message_bus
from agent_factory import create_agent
import threading

MAIN_AGENT_NAME = "nanoAgent"


def main() -> None:
    message_bus.register(MAIN_AGENT_NAME, "leader")

    run_thread = threading.Thread(target=nanoAgent.run_loop, daemon=True)
    run_thread.start()

    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in {"quit", "exit"}:
            break
        result = message_bus.send(None, to=MAIN_AGENT_NAME, content=text)


# ── create nanoAgent ──

nanoAgent = create_agent(
    name="nanoAgent",
    role="leader",
    profile="main",
    extra_registry={
        "sub_agent_task_tool": sub_agent_task_tool_instance,
        "spawn": spawn_tool_instance,
    },
)


if __name__ == "__main__":
    main()
