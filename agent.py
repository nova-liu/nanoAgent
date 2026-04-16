from client import client
import json, threading, traceback
from queue import Queue
from tools.tool_message_bus import message_bus
from tools.tool import Tool
from agent_context import AgentContext
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCallUnion,
)

IDLE = "idle"
THINKING = "thinking"
ACTING = "acting"


class Agent:
    def __init__(
        self,
        model="doubao-seed-2-0-code-preview-260215",
        max_tokens=8000,
        tools: list[Tool] = None,
        client=client,
        name="nanoAgent",
        max_context_tokens=1600,
        role="leader",
        system_template="Your name is {name} and your role is {role}.",
    ):
        self.context = AgentContext(
            name,
            role,
            client=client,
            messages=[
                {
                    "role": "system",
                    "content": system_template.format(name=name, role=role),
                }
            ],
        )
        self.tools = tools
        self._state = IDLE
        self.model = model
        self.max_tokens = max_tokens
        self.max_context_tokens = max_context_tokens
        self.response_queue: Queue[str] = Queue()

    def _set_state(self, state: str):
        self._state = state

    def run_loop(self):
        self._set_state(IDLE)
        while True:
            raw = message_bus.recv(self.context.name, timeout=3)
            if not raw:
                continue
            self.context.messages.append(
                {"role": "user", "content": f"<inbox>{raw}</inbox>"}
            )
            self._set_state(THINKING)
            try:
                self.one_task()
            except Exception as e:
                pass
            finally:
                self._set_state(IDLE)

    def one_task(self):
        while True:
            msg = self._completions_chat_non_stream()
            assistant_msg = {"role": msg.role or "assistant"}
            if msg.content:
                assistant_msg["content"] = msg.content

            self.context.messages.append(assistant_msg)

            if not msg.tool_calls:
                reply = msg.content or ""
                self.response_queue.put(reply)
                break

            self.handle_tool_calls(msg.tool_calls)

    def handle_tool_calls(self, tool_calls: list[ChatCompletionMessageToolCallUnion]):
        self._set_state(ACTING)
        for tc in tool_calls:
            # Prefer OpenAI SDK object-style access, keep dict fallback for compatibility.
            tool_name = tc.function.name
            raw_arguments = tc.function.arguments or ""
            tool_call_id = tc.id
            result = self._use_tool(tool_name, args)
            self.context.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result,
                }
            )

    def _use_tool(self, name: str, args: dict) -> str:
        try:
            tool = next((t for t in self.tools if t.name == name), None)
            if not tool:
                return f"Tool '{name}' not found"
            result = tool.do(self.context, args)
            return result
        except Exception as e:
            return f"Error using tool '{name}': {str(e)}"

    def _completions_chat_non_stream(self) -> ChatCompletionMessage:
        tool_contents = [t.content for t in self.tools]
        response = self.context.client.chat.completions.create(
            model=self.model,
            messages=self.context.messages,
            stream=False,
            tools=tool_contents,
            max_tokens=self.max_tokens,
            n=1,
        )
        return response.choices[0].message
