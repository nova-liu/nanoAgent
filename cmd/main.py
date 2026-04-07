import threading
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_spawn import spawn_tool_instance
from tool_message_bus import message_bus
from agent_factory import create_agent
from events import subscribe, Event, IDLE, THINKING, ACTING

USER_TAG = "[USER]"
OPS_TAG = "[OPS]"
SYSTEM_TAG = "[SYS]"


# ── shared write lock — all terminal output goes through this ──
_io_lock = threading.Lock()

# track per-agent state for status bar
_agent_states: dict[str, str] = {}

# track which agent is currently mid-stream (to collapse thinking line)
_streaming_agent: str | None = None

# prompt session created at runtime, used for toolbar refreshes
_session: PromptSession | None = None


def _write(*parts: str):
    """Atomic write to stdout."""
    with _io_lock:
        sys.stdout.write("".join(parts))
        sys.stdout.flush()


# ── status bar ──

def _build_status_text() -> str:
    agents = message_bus.list_agents()
    parts = []
    for a in agents:
        name = a["name"]
        role = a["role"]
        state = _agent_states.get(name, IDLE)
        qn = message_bus.pending_count(name)

        if state == THINKING:
            indicator = "T"
        elif state == ACTING:
            indicator = "A"
        else:
            indicator = "I"

        label = f"[{indicator}] {name}({role})"
        if state != IDLE:
            label += f" {state}"
        if qn > 0:
            label += f" q={qn}"
        parts.append(label)

    return "  ".join(parts) if parts else "(no agents)"


def bottom_toolbar():
    return f" {_build_status_text()} "


def render_status_bar():
    _write(f"--- {_build_status_text()} ---\n")
    if _session and _session.app and _session.app.is_running:
        _session.app.invalidate()


# ── event handler (subscriber) ──

def on_event(event: Event):
    """Route agent events to the correct terminal lane."""
    global _streaming_agent
    name = event.agent
    kind = event.kind
    d = event.data

    # ── state_changed ──
    if kind == "state_changed":
        _agent_states[name] = d["state"]

        # Keep state visualization in the bottom toolbar; only print a snapshot
        # when agent becomes idle so scrollback has milestones.
        if d["state"] == IDLE:
            render_status_bar()
        elif d["state"] == THINKING:
            _write(f"{OPS_TAG} {name} thinking...\n")
        elif _session and _session.app and _session.app.is_running:
            _session.app.invalidate()
        return

    # ── stream lifecycle ──
    if kind == "stream_start":
        _streaming_agent = name
        is_main = (name == "mainAgent")
        if is_main:
            _write(f"\n{USER_TAG} [{name}]: ")
        else:
            _write(f"\n{OPS_TAG} [{name}]: ")
        return

    if kind == "stream_delta":
        text = d.get("text", "")
        if text:
            _write(text)
        return

    if kind == "stream_end":
        _write("\n")
        _streaming_agent = None
        return

    # ── tool calls (ops lane — always dimmed) ──
    if kind == "tool_start":
        _write(
            f"{OPS_TAG} -> {d['tool']}"
            f" {d['args']}\n"
        )
        return

    if kind == "tool_end":
        _write(
            f"{OPS_TAG} <- {d['result']}\n"
        )
        return

    # ── errors ──
    if kind == "error":
        _write(
            f"\n{OPS_TAG} [{name}] ERROR:\n{d['traceback']}\n"
        )
        return

    # ── bus events (optional, for future use) ──
    if kind == "bus_event":
        _write(f"{OPS_TAG} [{d.get('summary', '')}]\n")
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

    print("nanoAgent 聊天室")
    print("直接输入文字和 leader 对话，leader 会自动路由给合适的 agent。")
    print("Ctrl+C 清空输入，Ctrl+D 或输入 quit 退出。")

    _session = PromptSession()

    with patch_stdout():
        while True:
            try:
                user_input = _session.prompt(
                    "> ",
                    bottom_toolbar=bottom_toolbar,
                )

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
                        f"{SYSTEM_TAG} mainAgent is {state}, "
                        f"message queued (position {qn + 1})\n"
                    )

            except KeyboardInterrupt:
                # Keep the app running; clear current input line.
                continue
            except EOFError:
                break
            except Exception as e:
                _write(f"[error]: {e}\n")
