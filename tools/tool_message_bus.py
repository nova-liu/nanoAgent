"""
Thread-safe in-memory message bus with per-agent queues.

Each agent has a Queue.  Messages are delivered instantly (no file I/O).
The bus is a process-wide singleton and the **single source of truth**
for which agents are online — registered = online, no heartbeat files.
"""

import json
import threading
import time
from queue import Queue, Empty
from tools.tool import Tool
from agent_context import AgentContext


class MessageBus:
    def __init__(self):
        self._queues: dict[str, Queue] = {}
        self._roles: dict[str, str] = {}  # name -> role
        self._lock = threading.Lock()

    # ── registration (online / offline) ──
    def register(self, name: str, role: str = "unknown"):
        """Mark *name* as online and create its inbox queue."""
        with self._lock:
            if name not in self._queues:
                self._queues[name] = Queue()
            self._roles[name] = role

    def is_online(self, name: str) -> bool:
        with self._lock:
            return name in self._roles

    def list_agents(self, agent_context: AgentContext | None = None) -> list[dict]:
        """Return every registered agent with its role."""
        with self._lock:
            return [
                {"name": n, "role": r, "status": "online"}
                for n, r in sorted(self._roles.items())
            ]

    # ── messaging ──

    def send(
        self,
        agent_context: AgentContext | None,
        to: str,
        content: str,
    ) -> str:
        if not self.is_online(to):
            return (
                f'Error: "{to}" is offline. '
                f"Use spawn to start it first, or pick another online agent."
            )

        sender = "user"
        if agent_context and hasattr(agent_context, "name"):
            sender = agent_context.name

        msg = {
            "sender": sender,
            "content": content,
            "timestamp": time.time(),
        }
        with self._lock:
            q = self._queues.get(to)
        if q is None:
            return f'Error: "{to}" went offline.'
        q.put(msg)
        return f"Sent message to {to}"

    def recv(self, name: str, timeout: float = 0) -> str:
        """
        Read all pending messages for *name*.
        Returns JSON array string, or empty string if nothing.
        If timeout > 0, blocks up to that many seconds for the first message.
        """
        with self._lock:
            q = self._queues.get(name)
        if q is None:
            return ""
        messages = []

        # Optionally block for first message
        if timeout > 0 and q.empty():
            try:
                first = q.get(timeout=timeout)
                messages.append(first)
            except Empty:
                return ""

        # Drain remaining
        while True:
            try:
                messages.append(q.get_nowait())
            except Empty:
                break

        if not messages:
            return ""
        return json.dumps(messages, ensure_ascii=False)


# Singleton
message_bus = MessageBus()

# ── Tool definitions ──
send_message_tool = {
    "type": "function",
    "function": {
        "name": "send_message",
        "description": (
            "Send a message to an online agent. "
            "Sender is auto-filled. Will FAIL if recipient is offline — spawn first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient agent name"},
                "content": {"type": "string", "description": "Message content"},
            },
            "required": ["to", "content"],
        },
    },
}

send_message_tool_instance = Tool(
    name="send_message", content=send_message_tool, function=message_bus.send
)

NAME = "list_agents"
members_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "List all ONLINE teammates with their roles. Only shows agents that are currently running and reachable.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "required": [],
    },
}

list_agents_tool_instance = Tool(
    name=NAME, content=members_tool, function=message_bus.list_agents
)
