from client import client
import time, json, threading
import json
from agent_logger import AgentLogger, step
from tool_message_bus import message_bus
from tool import Tool
from agent_context import AgentContext

print_lock = threading.Lock()


class Agent:
    def __init__(
        self,
        model="doubao-seed-2-0-code-preview-260215",
        max_tokens=8000,
        tools: list[Tool] = None,
        client=client,
        name="mainAgent",
        max_context_tokens=1600,
        role="leader",
        system_template="Your name is {name} and your role is {role}.",
    ):
        self.context = AgentContext(
            name,
            role,
            system_template,
            model,
            client,
            max_tokens,
            max_context_tokens,
        )
        self.tools = tools
        self.logger = AgentLogger(name)

    def run_loop(self):
        while True:
            message = message_bus.read_inbox(self.context, self.context.name)
            if not message:
                time.sleep(3)
                continue
            self.context.messages.append(
                {"role": "user", "content": f"<inbox>{message}</inbox>"}
            )

            self.one_task()

    def one_task(self):
        while True:
            content, _, role, tool_calls_list = self._stream_chat()
            # append the assistant message to the conversation, including any tool calls or refusals
            if content:
                self.context.messages.append({"role": role, "content": content})

            if not tool_calls_list:
                break

            # need to run the tool calls and append the results to the conversation before the next turn
            self.handle_tool_calls(tool_calls_list)

    def handle_tool_calls(self, tool_calls_list):
        for tc in tool_calls_list:
            args = json.loads(tc["function"]["arguments"])
            result = self._use_tool(tc["function"]["name"], args)
            self.context.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
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

    def _chat_log(self, content: str, refusal: str, role: str, tool_calls_list: list):
        # LLM step
        with step(self.logger, "llm", "chat") as s:
            s.set_input(
                {
                    "messages": self.context.messages,
                }
            )

            s.set_output(
                {
                    "content": content,
                    "refusal": refusal,
                    "role": role,
                    "tool_calls": tool_calls_list,
                }
            )

        self.logger.finish()
        self.logger.save()

    def _stream_chat(self) -> tuple[str, str, str, list]:
        tool_contents = [t.content for t in self.tools]
        stream = self.context.client.chat.completions.create(
            model=self.context.model,
            messages=self.context.messages,
            stream=True,
            tools=tool_contents,
            max_tokens=self.context.max_tokens,
            n=1,
        )

        content = ""
        refusal = ""
        role = ""
        tool_calls_dict = {}
        with print_lock:
            print(f"\n[{self.context.name}]: ", end="", flush=True)

            for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    content += delta.content
                    print(delta.content, end="", flush=True)

                if delta.refusal:
                    refusal += delta.refusal
                    print(delta.refusal, end="", flush=True)

                if delta.role and not role:
                    role += delta.role
                # 2️⃣ tool call（重点）
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index

                        if idx not in tool_calls_dict:
                            tool_calls_dict[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }

                        if tc.id:
                            tool_calls_dict[idx]["id"] = tc.id

                        if tc.function:
                            if tc.function.name:
                                tool_calls_dict[idx]["name"] = tc.function.name

                            if tc.function.arguments:
                                tool_calls_dict[idx][
                                    "arguments"
                                ] += tc.function.arguments

                if choice.finish_reason:
                    break

        tool_calls_list = build_tool_calls(tool_calls_dict)

        self._chat_log(content, refusal, role, tool_calls_list)
        return content, refusal, role, tool_calls_list


def build_tool_calls(tool_calls_dict: dict) -> list:
    tool_calls = []

    for i in sorted(tool_calls_dict.keys()):
        tc = tool_calls_dict[i]

        tool_calls.append(
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            }
        )

    return tool_calls
