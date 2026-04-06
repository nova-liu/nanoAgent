from client import client
import time
import json
from agent_logger import AgentLogger, step
from tool_message_bus import message_bus
from tool import Tool
from agent_context import AgentContext
from openai.types.chat.chat_completion import ChatCompletion


class Agent:
    def __init__(
        self,
        model="doubao-seed-1-8-251228",
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
                print("No new messages. Waiting...")
                time.sleep(3)
                continue
            self.context.messages.append(
                {"role": "user", "content": f"<inbox>{message}</inbox>"}
            )

            self.one_task()

    def one_task(self):
        while True:
            response = self.call_llm()
            msg = response.choices[0].message
            # append the assistant message to the conversation, including any tool calls or refusals
            if msg.content:
                self.context.messages.append(
                    {"role": "assistant", "content": msg.content}
                )

            if not msg.tool_calls:
                break

            # need to run the tool calls and append the results to the conversation before the next turn
            self.handle_tool_calls(msg)

    def call_llm(self):
        tool_contents = [t.content for t in self.tools]
        response = self.context.client.chat.completions.create(
            model=self.context.model,
            messages=self.context.messages,
            tools=tool_contents,
            max_tokens=self.context.max_tokens,
            n=1,
        )
        self._chat_log(response)

        return response

    def handle_tool_calls(self, msg):
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = self._use_tool(tc.function.name, args)
            self.context.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
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

    def _chat_log(self, response: ChatCompletion):
        # LLM step
        with step(self.logger, "llm", "chat") as s:
            s.set_input(
                {
                    "messages": self.context.messages,
                }
            )
            msg = response.choices[0].message
            tool_calls = (
                [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
                if msg.tool_calls
                else []
            )

            s.set_output(
                {
                    "content": msg.content,
                    "refusal": msg.refusal,
                    "role": msg.role,
                    "tool_calls": tool_calls,
                }
            )

            if msg.tool_calls:
                s.set_output(
                    {
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ]
                    }
                )

        self.logger.finish()
        self.logger.save()
