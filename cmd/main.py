import threading

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Input, Static

from tool_sub_agent_task import sub_agent_task_tool_instance
from tool_spawn import spawn_tool_instance
from tool_message_bus import message_bus
from agent_factory import create_agent
from events import subscribe, Event, IDLE, THINKING, ACTING

USER_TAG = "[USER]"
AGENT_TAG = "[AGENT]"
OPS_TAG = "[OPS]"
SYSTEM_TAG = "[SYS]"
MAIN_AGENT_NAME = "nanoAgent"


class MessageBubble(Static):
    def __init__(self, text: str, classes: str = ""):
        super().__init__(text, classes=classes)


class NanoAgentIM(App):
    TITLE = "nanoAgent IM"
    CSS = """
    Screen {
        layout: vertical;
        background: #0d1117;
        color: #f0f6fc;
    }

    #chat {
        height: 1fr;
        padding: 1 2;
    }

    .row {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    .pad {
        width: 1fr;
    }

    .bubble {
        width: auto;
        max-width: 70%;
        padding: 0 1;
        border: round #39424e;
    }

    .agent-bubble {
        background: #13233a;
        color: #dbeafe;
    }

    .main-reply-bubble {
        background: #1b3f2a;
        color: #dcfce7;
        border: round #59c28a;
        text-style: bold;
    }

    .user-bubble {
        background: #1f3b2e;
        color: #dcfce7;
    }

    .ops-bubble {
        background: #20242c;
        color: #9ca3af;
    }

    .background-bubble {
        background: #1b1f26;
        color: #8b95a7;
        border: round #2f3542;
    }

    .system-bubble {
        background: #2a1e11;
        color: #fde68a;
    }

    #status {
        height: 1;
        color: #93c5fd;
        background: #111827;
        padding: 0 1;
    }

    #input {
        height: 3;
        margin: 0 1;
        border: round #2f3542;
        background: #161b22;
        color: #f0f6fc;
    }
    """

    agent_states = reactive(dict)

    def __init__(self):
        super().__init__()
        self._stream_buffers: dict[str, list[str]] = {}
        self._run_thread: threading.Thread | None = None

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat")
        yield Static("", id="status")
        yield Input(
            placeholder="Type a message, Enter to send. '/quit' to exit.", id="input"
        )

    def on_mount(self) -> None:
        message_bus.register("nanoAgent", "leader")
        subscribe(self._on_event_from_agents)

        self._run_thread = threading.Thread(target=nanoAgent.run_loop, daemon=True)
        self._run_thread.start()

        self._add_system_message("nanoAgent IM started. nanoAgent is online.")
        self._refresh_status()
        self.query_one("#input", Input).focus()

    @on(Input.Submitted, "#input")
    def submit_message(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return

        if text.startswith("/"):
            if self._handle_slash_command(text):
                self._refresh_status()
                return
            self._add_ops_message(
                f"{SYSTEM_TAG} Unknown command: {text}. Try /help for available commands."
            )
            self._refresh_status()
            return

        if text.lower() in {"quit", "exit", "/quit"}:
            self.exit()
            return

        self._add_user_message(text)
        qn = message_bus.pending_count("nanoAgent")
        message_bus.send(None, to="nanoAgent", content=text)

        state = self.agent_states.get("nanoAgent", IDLE)
        if state != IDLE:
            self._add_ops_message(
                f"{SYSTEM_TAG} nanoAgent is {state}, queued at position {qn + 1}"
            )
        else:
            self._add_ops_message(f"{SYSTEM_TAG} sent to nanoAgent")

        self._refresh_status()

    def _handle_slash_command(self, command: str) -> bool:
        lowered = command.lower()

        if lowered in {"/help", "/h"}:
            self._show_help()
            return True

        if lowered in {"/agents", "/members", "/status"}:
            self._add_system_message(self._render_agents_snapshot())
            return True

        if lowered == "/clear":
            self._clear_chat()
            self._add_system_message("chat cleared")
            return True

        if lowered in {"/quit", "/exit"}:
            self.exit()
            return True

        return False

    def _show_help(self) -> None:
        self._add_system_message(
            "Commands: /help, /agents, /status, /clear, /quit. "
            "Plain text messages are sent to nanoAgent."
        )

    def _render_agents_snapshot(self) -> str:
        agents = message_bus.list_agents()
        if not agents:
            return "no agents online"

        rows = []
        for item in agents:
            name = item["name"]
            role = item["role"]
            state = self.agent_states.get(name, IDLE)
            queue_count = message_bus.pending_count(name)
            rows.append(f"{name}({role}) state={state} queue={queue_count}")
        return "online agents: " + " | ".join(rows)

    def _clear_chat(self) -> None:
        chat = self.query_one("#chat", VerticalScroll)
        for child in list(chat.children):
            child.remove()

    def _on_event_from_agents(self, event: Event) -> None:
        # Event callback runs on worker threads; schedule UI updates safely.
        self.call_from_thread(self._handle_event_on_ui, event)

    def _handle_event_on_ui(self, event: Event) -> None:
        name = event.agent
        kind = event.kind
        data = event.data
        is_main = name == MAIN_AGENT_NAME

        if kind == "state_changed":
            self.agent_states[name] = data.get("state", IDLE)
            self._refresh_status()
            return

        if kind == "stream_start":
            self._stream_buffers[name] = []
            return

        if kind == "stream_delta":
            text = data.get("text", "")
            if text:
                self._stream_buffers.setdefault(name, []).append(text)
            return

        if kind == "stream_end":
            content = "".join(self._stream_buffers.pop(name, []))
            if content.strip():
                if is_main:
                    self._add_main_reply(name, content)
                else:
                    self._add_background_message(name, content)
            return

        if kind == "tool_start":
            self._add_background_message(
                name,
                f"{OPS_TAG} -> {data.get('tool')} {data.get('args')}",
            )
            return

        if kind == "tool_end":
            self._add_background_message(name, f"{OPS_TAG} <- {data.get('result')}")
            return

        if kind == "error":
            traceback_text = data.get("traceback", "")
            summary = traceback_text.strip().splitlines()[-1] if traceback_text else ""
            self._add_background_message(
                name, f"{OPS_TAG} ERROR: {summary or 'unknown error'}"
            )
            return

        if kind == "bus_event":
            self._add_background_message(name, f"{OPS_TAG} {data.get('summary', '')}")
            return

    def _append_bubble(self, text: str, side: str, bubble_class: str) -> None:
        chat = self.query_one("#chat", VerticalScroll)
        bubble = MessageBubble(text, classes=f"bubble {bubble_class}")
        pad = Static("", classes="pad")

        if side == "right":
            row = Horizontal(pad, bubble, classes="row")
        else:
            row = Horizontal(bubble, pad, classes="row")

        chat.mount(row)
        chat.scroll_end(animate=False)

    def _add_user_message(self, text: str) -> None:
        self._append_bubble(f"user: {text}", side="right", bubble_class="user-bubble")

    def _add_agent_message(self, name: str, text: str) -> None:
        self._append_bubble(
            f"{name}: {text}",
            side="left",
            bubble_class="agent-bubble",
        )

    def _add_main_reply(self, name: str, text: str) -> None:
        self._append_bubble(
            f"{name}: {text}",
            side="left",
            bubble_class="main-reply-bubble",
        )

    def _add_background_message(self, name: str, text: str) -> None:
        self._append_bubble(
            f"{name}: {text}",
            side="left",
            bubble_class="background-bubble",
        )

    def _add_ops_message(self, text: str) -> None:
        self._append_bubble(text, side="left", bubble_class="ops-bubble")

    def _add_system_message(self, text: str) -> None:
        self._append_bubble(
            f"{SYSTEM_TAG} {text}", side="left", bubble_class="system-bubble"
        )

    def _refresh_status(self) -> None:
        agents = message_bus.list_agents()
        parts = []
        for item in agents:
            name = item["name"]
            role = item["role"]
            state = self.agent_states.get(name, IDLE)
            queue_count = message_bus.pending_count(name)

            if state == THINKING:
                indicator = "T"
            elif state == ACTING:
                indicator = "A"
            else:
                indicator = "I"

            label = f"[{indicator}] {name}({role})"
            if state != IDLE:
                label += f" {state}"
            if queue_count:
                label += f" q={queue_count}"
            parts.append(label)

        status = "  ".join(parts) if parts else "(no agents online)"
        self.query_one("#status", Static).update(status)


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
    NanoAgentIM().run()
