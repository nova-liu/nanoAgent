from client import client
import json, threading, traceback
from agent_logger import AgentLogger, step
from tool_message_bus import message_bus
from tool import Tool
from agent_context import AgentContext

IDLE = "idle"
THINKING = "thinking"
ACTING = "acting"

_print_lock = threading.Lock()


def console_log(agent_name: str, message: str) -> None:
    with _print_lock:
        print(f"{agent_name}: {message}", flush=True)


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
            system_template,
            model,
            client,
            max_tokens,
            max_context_tokens,
        )
        self.tools = tools
        self.logger = AgentLogger(name)
        self._state = IDLE

    def _set_state(self, state: str):
        self._state = state
        if state != IDLE:
            console_log(self.context.name, f"[{state}]")

    def run_loop(self):
        message_bus.register(self.context.name, self.context.role)
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
            except Exception:
                tb = traceback.format_exc()
                summary = tb.strip().splitlines()[-1] if tb else "unknown error"
                console_log(self.context.name, f"ERROR: {summary}")
            finally:
                self._set_state(IDLE)

    def one_task(self):
        while True:
            content, _, role, tool_calls_list = self._stream_chat()
            assistant_msg = {"role": role or "assistant"}
            if content:
                assistant_msg["content"] = content
            if tool_calls_list:
                assistant_msg["tool_calls"] = tool_calls_list
            if content or tool_calls_list:
                self.context.messages.append(assistant_msg)

            if not tool_calls_list:
                break

            self.handle_tool_calls(tool_calls_list)

            # Back to thinking before next LLM round
            self._set_state(THINKING)

    def handle_tool_calls(self, tool_calls_list):
        self._set_state(ACTING)
        for tc in tool_calls_list:
            tool_name = tc["function"]["name"]
            raw_arguments = tc["function"].get("arguments", "")
            try:
                args = json.loads(raw_arguments) if raw_arguments else {}
            except json.JSONDecodeError as e:
                error_result = (
                    f"Error using tool '{tool_name}': invalid JSON arguments ({e})"
                )
                console_log(self.context.name, error_result)
                self.context.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": error_result,
                    }
                )
                continue

            args_brief = json.dumps(args, ensure_ascii=False)
            if len(args_brief) > 120:
                args_brief = args_brief[:117] + "..."
            console_log(self.context.name, f"-> {tool_name} {args_brief}")

            result = self._use_tool(tool_name, args)

            result_brief = result.replace("\n", " ")
            if len(result_brief) > 120:
                result_brief = result_brief[:117] + "..."
            console_log(self.context.name, f"<- {result_brief}")

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

        for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                content += delta.content

            if delta.refusal:
                refusal += delta.refusal

            if delta.role and not role:
                role += delta.role

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
                            tool_calls_dict[idx]["arguments"] += tc.function.arguments

            if choice.finish_reason:
                break

        if content.strip():
            console_log(self.context.name, content)
        elif refusal.strip():
            console_log(self.context.name, refusal)

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
