from client import client
import time, json, threading, traceback
from agent_logger import AgentLogger, step
from tool_message_bus import message_bus
from tool import Tool
from agent_context import AgentContext
import sys

print_lock = threading.Lock()

# callback set by the entrypoint to refresh UI after agent output
on_agent_output_done = None


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
        name_palette = [
            "\033[96m",  # cyan
            "\033[92m",  # green
            "\033[94m",  # blue
            "\033[93m",  # yellow
            "\033[91m",  # red
            "\033[95m",  # magenta
        ]
        idx = sum(ord(c) for c in name) % len(name_palette)
        self.name_color = name_palette[idx]
        self.text_color = "\033[97m"
        self.reset_color = "\033[0m"
        self.tools = tools
        self.logger = AgentLogger(name)

    def _show_thinking(self):
        """Display a thinking… indicator for this agent."""
        with print_lock:
            sys.stdout.write(
                f"\n{self.name_color}[{self.context.name}]{self.reset_color}"
                f" \033[2mthinking…\033[0m"
            )
            sys.stdout.flush()
        self._thinking = True

    def _clear_thinking(self):
        """Erase the thinking indicator if it's still visible."""
        if getattr(self, "_thinking", False):
            with print_lock:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
            self._thinking = False

    def run_loop(self):
        message_bus.register(self.context.name, self.context.role)
        while True:
            raw = message_bus.recv(self.context.name, timeout=3)
            if not raw:
                continue
            self.context.messages.append(
                {"role": "user", "content": f"<inbox>{raw}</inbox>"}
            )

            self._show_thinking()

            try:
                self.one_task()
            except Exception:
                self._clear_thinking()
                tb = traceback.format_exc()
                with print_lock:
                    sys.stdout.write(
                        f"\n{self.name_color}[{self.context.name}]{self.reset_color}"
                        f" \033[91mERROR:\033[0m\n\033[2m{tb}\033[0m\n"
                    )
                    sys.stdout.flush()

    def one_task(self):
        while True:
            content, _, role, tool_calls_list = self._stream_chat()
            # Append the assistant message — must include tool_calls when present
            # so the API sees them paired with subsequent tool-result messages.
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

            # Show thinking again before the next LLM round
            self._show_thinking()

    def handle_tool_calls(self, tool_calls_list):
        for tc in tool_calls_list:
            tool_name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])

            # Show tool usage in terminal
            with print_lock:
                args_brief = json.dumps(args, ensure_ascii=False)
                if len(args_brief) > 120:
                    args_brief = args_brief[:117] + "..."
                sys.stdout.write(
                    f"  {self.name_color}↳ {tool_name}{self.reset_color}"
                    f" \033[2m{args_brief}\033[0m\n"
                )
                sys.stdout.flush()

            result = self._use_tool(tool_name, args)

            # Show result snippet
            with print_lock:
                result_brief = result.replace("\n", " ")
                if len(result_brief) > 120:
                    result_brief = result_brief[:117] + "..."
                sys.stdout.write(
                    f"  {self.name_color}  ← {self.reset_color}"
                    f"\033[2m{result_brief}\033[0m\n"
                )
                sys.stdout.flush()

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
            # Clear "thinking…" line if it's still showing
            if getattr(self, "_thinking", False):
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                self._thinking = False
            sys.stdout.write(
                f"\n{self.name_color}[{self.context.name}]: {self.text_color}"
            )
            sys.stdout.flush()
            for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    content += delta.content
                    # 使用 sys.stdout.write 配合 flush，在 M4 Mac 上体验极佳
                    sys.stdout.write(delta.content)
                    sys.stdout.flush()

                if delta.refusal:
                    refusal += delta.refusal
                    sys.stdout.write(delta.refusal)
                    sys.stdout.flush()

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

            sys.stdout.write(f"{self.reset_color}\n")
            sys.stdout.flush()

        if on_agent_output_done:
            on_agent_output_done()

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
