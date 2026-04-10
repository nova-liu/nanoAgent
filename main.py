from tools.tool_message_bus import message_bus
from agent_factory import create_agent
import threading

MAIN_AGENT_NAME = "nanoAgent"
MAIN_AGENT_ROLE = "leader"


def main() -> None:
    message_bus.register(MAIN_AGENT_NAME, MAIN_AGENT_ROLE)
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
    name=MAIN_AGENT_NAME,
    role=MAIN_AGENT_ROLE,
    profile="main",
)


if __name__ == "__main__":
    main()
