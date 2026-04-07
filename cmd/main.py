import threading
import sys

from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_spawn import spawn_tool_instance
from tool_message_bus import message_bus
from agent_factory import create_agent
from events import subscribe, Event, IDLE, THINKING, ACTING

# ── colours ──
DIM = "\033[2m"
BOLD = "\033[1m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"

# per-agent colour palette (assigned by name hash)
_NAME_PALETTE = [
    "\033[96m",  # cyan
    "\033[92m",  # green
    "\033[94m",  # blue
    "\033[93m",  # yellow
    "\033[91m",  # red
    "\033[95m",  # magenta
]


def _agent_color(name: str) -> str:
    return _NAME_PALETTE[sum(ord(c) for c in name) % len(_NAME_PALETTE)]


# ── shared write lock — all terminal output goes through this ──
_io_lock = threading.Lock()

# track per-agent state for status bar
_agent_states: dict[str, str] = {}

# track which agent is currently mid-stream (to collapse thinking line)
_streaming_agent: str | None = None


def _write(*parts: str):
    """Atomic write to stdout."""
    with _io_lock:
        sys.stdout.write("".join(parts))
        sys.stdout.flush()


# ── status bar ──

def render_status_bar():
    agents = message_bus.list_agents()
    parts = []
    for a in agents:
        name = a["name"]
        role = a["role"]
        state = _agent_states.get(name, IDLE)
        qn = message_bus.pending_count(name)

        color = _agent_color(name)

        # state indicator
        if state == THINKING:
            indicator = f"{YELLOW}◉{RESET}"
        elif state == ACTING:
            indicator = f"{RED}⚡{RESET}"
        else:
            indicator = f"{GREEN}●{RESET}"

        label = f"{indicator} {color}{name}{RESET}({DIM}{role}{RESET})"
        if state != IDLE:
            label += f" {DIM}{state}{RESET}"
        if qn > 0:
            label += f" {YELLOW}q={qn}{RESET}"
        parts.append(label)

    bar = "  ".join(parts) if parts else f"{DIM}(no agents){RESET}"
    _write(f"\n{DIM}─── {bar} {DIM}───{RESET}\n")


# ── event handler (subscriber) ──

def on_event(event: Event):
    """Route agent events to the correct terminal lane."""
    global _streaming_agent
    name = event.agent
    color = _agent_color(name)
    kind = event.kind
    d = event.data

    # ── state_changed ──
    if kind == "state_changed":
        _agent_states[name] = d["state"]

        if d["state"] == THINKING:
            # Show thinking indicator (will be overwritten by stream_start)
            _write(f"\n{color}[{name}]{RESET} {DIM}thinking…{RESET}")
        elif d["state"] == IDLE:
            render_status_bar()
        return

    # ── stream lifecycle ──
    if kind == "stream_start":
        _streaming_agent = name
        # Erase the thinking line, then print [name]: header
        is_main = (name == "mainAgent")
        if is_main:
            _write(f"\r\033[K\n{color}{BOLD}[{name}]:{RESET} ")
        else:
            _write(f"\r\033[K\n{DIM}{color}[{name}]:{RESET}{DIM} ")
        return

    if kind == "stream_delta":
        text = d.get("text", "")
        if text:
            _write(text)
        return

    if kind == "stream_end":
        is_main = (name == "mainAgent")
        if not is_main:
            _write(f"{RESET}")   # close DIM for non-main agents
        _write(f"{RESET}\n")
        _streaming_agent = None
        return

    # ── tool calls (ops lane — always dimmed) ──
    if kind == "tool_start":
        _write(
            f"  {color}↳ {d['tool']}{RESET}"
            f" {DIM}{d['args']}{RESET}\n"
        )
        return

    if kind == "tool_end":
        _write(
            f"  {color}  ← {RESET}"
            f"{DIM}{d['result']}{RESET}\n"
        )
        return

    # ── errors ──
    if kind == "error":
        _write(
            f"\n{color}[{name}]{RESET}"
            f" {RED}ERROR:{RESET}\n{DIM}{d['traceback']}{RESET}\n"
        )
        return

    # ── bus events (optional, for future use) ──
    if kind == "bus_event":
        _write(f"{DIM}  [{d.get('summary', '')}]{RESET}\n")
        return


# ── create mainAgent ──

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
    # Pre-register mainAgent queue so user messages arrive before run_loop starts
    message_bus.register("mainAgent", "leader")

    # Wire up event system
    subscribe(on_event)

    thread = threading.Thread(
        target=mainAgent.run_loop,
        args=(),
        daemon=True,
    )
    thread.start()

    print(f"{YELLOW}nanoAgent 聊天室{RESET}")
    print(f"{DIM}直接输入文字和 leader 对话，leader 会自动路由给合适的 agent。{RESET}")
    print(f"{DIM}输入 quit 或 exit 退出。{RESET}")

    render_status_bar()

    while True:
        try:
            user_input = input(f"{CYAN}> {RESET}")

            if user_input.strip().lower() in ["quit", "exit"]:
                break

            if not user_input.strip():
                continue

            # Send and give immediate receipt
            qn = message_bus.pending_count("mainAgent")
            message_bus.send(None, to="mainAgent", content=user_input)

            state = _agent_states.get("mainAgent", IDLE)
            if state != IDLE:
                _write(
                    f"{DIM}  ⏳ mainAgent is {state}, "
                    f"message queued (position {qn + 1}){RESET}\n"
                )

        except KeyboardInterrupt:
            print()
            break
        except Exception as e:
            _write(f"{YELLOW}[error]: {e}{RESET}\n")
