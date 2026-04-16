from tools.tool_message_bus import message_bus
from agent_factory import create_agent
import sys
import threading
import itertools

MAIN_AGENT_NAME = "nanoAgent"
MAIN_AGENT_ROLE = "leader"


def _spinner(stop_event: threading.Event):
    """Print a thinking spinner until stop_event is set."""
    for ch in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        if stop_event.wait(0.1):
            break
        sys.stdout.write(f"\r\033[90m{ch} thinking...\033[0m")
        sys.stdout.flush()
    # clear the spinner line
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()


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

        message_bus.send(None, to=MAIN_AGENT_NAME, content=text)

        # show spinner while agent is thinking
        stop_spin = threading.Event()
        spin_thread = threading.Thread(target=_spinner, args=(stop_spin,), daemon=True)
        spin_thread.start()

        # block until agent produces a response
        reply = nanoAgent.response_queue.get()

        stop_spin.set()
        spin_thread.join()

        print(f"\n\033[1m{MAIN_AGENT_NAME}>\033[0m {reply}\n")


# ── create nanoAgent ──
nanoAgent = create_agent(
    name=MAIN_AGENT_NAME,
    role=MAIN_AGENT_ROLE,
    profile="main",
)


if __name__ == "__main__":
    main()
