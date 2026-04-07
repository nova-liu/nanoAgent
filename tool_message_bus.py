from pathlib import Path
import json
import time
from config import INBOX_DIR
from tool import Tool
from agent_context import AgentContext
from team_state import is_online

VALID_MSG_TYPES = [
    "message",
    "shutdown",
]


# -- MessageBus: JSONL inbox per teammate --
class MessageBus:
    def __init__(self, inbox_dir: Path):
        self.dir = inbox_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def send(
        self,
        agent_context: AgentContext,
        to: str,
        content: str,
        msg_type: str = "message",
    ) -> str:
        if msg_type not in VALID_MSG_TYPES:
            return f"Error: Invalid type '{msg_type}'. Valid: {VALID_MSG_TYPES}"

        # Block sending to offline agents (except "user" / "mainAgent" from CLI)
        if to != "user" and not is_online(to):
            return (
                f"Error: '{to}' is offline. "
                f"Use `spawn` to start '{to}' first, or pick another online agent."
            )

        # Auto-derive sender from context
        sender = "user"
        if agent_context and hasattr(agent_context, "name"):
            sender = agent_context.name

        msg = {
            "type": msg_type,
            "sender": sender,
            "content": content,
            "timestamp": time.time(),
        }
        inbox_path = self.dir / f"{to}.jsonl"
        with open(inbox_path, "a") as f:
            f.write(json.dumps(msg) + "\n")
        return f"Sent {msg_type} to {to}"

    def read_inbox(self, agent_context: AgentContext, name: str) -> str:
        inbox_path = self.dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return ""
        messages = []
        for line in inbox_path.read_text().strip().splitlines():
            if line:
                msg = json.loads(line)
                messages.append(msg)
        ## clear inbox after reading
        inbox_path.write_text("")
        if len(messages) == 0:
            return ""
        return json.dumps(messages)


message_bus = MessageBus(INBOX_DIR)


send_message_tool = {
    "type": "function",
    "function": {
        "name": "send_message",
        "description": "Send a message to an online agent. Sender is auto-filled from your identity. Will fail if recipient is offline — use spawn first.",
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

read_inbox_tool = {
    "type": "function",
    "function": {
        "name": "read_inbox",
        "description": "Read and clear the inbox for a teammate.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Teammate name"},
            },
            "required": ["name"],
        },
    },
}

send_message_tool_instance = Tool(
    name="send_message", content=send_message_tool, function=message_bus.send
)

read_inbox_tool_instance = Tool(
    name="read_inbox", content=read_inbox_tool, function=message_bus.read_inbox
)
