from client import client
import time
import json
from log import logger
from tool_message_bus import message_bus
from tool import Tool
from agent_context import AgentContext

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
            logger.log_messages(self.context.name, self.context.messages)
            response = self.call_llm(self.context.messages)
            logger.log_response(self.context.name, response)
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

    def call_llm(self, messages=None):
        if messages is None:
            return
        tool_contents = [t.content for t in self.tools]
        response = self.context.client.chat.completions.create(
            model=self.context.model,
            messages=messages,
            tools=tool_contents,
            max_tokens=self.context.max_tokens,
            n=1,
        )

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
