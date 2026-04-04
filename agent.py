from client import client
import time
import json
from log import logger
from config import TRANSCRIPT_DIR
from message_bus import message_bus
from t import Tool


class Agent:
    def __init__(
        self,
        model="doubao-seed-1-8-251228",
        max_tokens=8000,
        tools: list[Tool] = None,
        client=client,
        sub_agent: "Agent" = None,
        name="mainAgent",
        logger=logger,
        transcript_dir=TRANSCRIPT_DIR,
        max_context_tokens=1600,
        role="leader",
        message_bus=message_bus,
        system_template="Your name is {name} and your role is {role}.",
    ):
        self.name = name
        self.role = role
        self.model = model
        self.tools = tools
        self.max_tokens = max_tokens
        self.messages = [
            {"role": "system", "content": system_template.format(name=name, role=role)}
        ]
        self.client = client
        self.sub_agent = sub_agent
        self.logger = logger
        self.transcript_dir = transcript_dir
        self.max_context_tokens = max_context_tokens
        self.threads = {}
        self.message_bus = message_bus

    def do_one_task(self, task: str) -> str:
        while True:
            self.append_user_message(task)
            self.log_messages()
            response = self.call_llm(self.messages)
            self.log_response(response)

            msg = response.choices[0].message
            # append the assistant message to the conversation, including any tool calls or refusals
            self.append_assistant_message(msg.content)

            if not msg.tool_calls:
                break
            # need to run the tool calls and append the results to the conversation before the next turn
            self.handle_tool_calls(msg)
        return self.final_response()

    def run_loop(self):
        while True:
            if self.estimate_tokens() > self.max_context_tokens:
                self.auto_compact()
            message = self.message_bus.read_inbox(self.name)
            print(f"[{self.name} inbox] {message}")
            if not message:
                print("No new messages. Waiting...")
                time.sleep(3)
                continue
            self.append_user_message(f"<inbox>{message}</inbox>")
            self.log_messages()
            while True:
                response = self.call_llm(self.messages)
                self.log_response(response)

                msg = response.choices[0].message
                # append the assistant message to the conversation, including any tool calls or refusals
                self.append_assistant_message(msg.content)

                if not msg.tool_calls:
                    break

                # need to run the tool calls and append the results to the conversation before the next turn
                self.handle_tool_calls(msg)

    def final_response(self) -> str:
        return self.messages[-1]["content"] if self.messages else ""

    def append_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def use_tool(self, name: str, args: dict) -> str:
        try:
            tool = next((t for t in self.tools if t.name == name), None)
            if not tool:
                return f"Tool '{name}' not found"
            result = tool.do(args)
            return result
        except Exception as e:
            return f"Error using tool '{name}': {str(e)}"

    def call_llm(self, messages=None):
        if messages is None:
            return
        tool_contents = [t.content for t in self.tools]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tool_contents,
            max_tokens=self.max_tokens,
            n=1,
        )
        return response

    def append_tool_response(self, tool_call_id: str, content: str):
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content,
            }
        )
        self.compact_tool_result()

    def append_assistant_message(self, content: str):
        if content:
            self.messages.append({"role": "assistant", "content": content})

    def log_messages(self):
        self.logger.log_messages(self.name, self.messages)

    def log_response(self, response):
        self.logger.log_response(self.name, response)

    def compact_tool_result(self):
        tool_indexes = [
            idx for idx, msg in enumerate(self.messages) if msg.get("role") == "tool"
        ]
        if len(tool_indexes) <= 3:
            return

        drop_indexes = set(tool_indexes[:-3])
        self.messages = [
            msg for idx, msg in enumerate(self.messages) if idx not in drop_indexes
        ]

    def auto_compact(self):
        self.transcript_dir.mkdir(exist_ok=True)
        transcript_path = self.transcript_dir / f"transcript_{int(time.time())}.jsonl"
        with open(transcript_path, "w") as f:
            for msg in self.messages:
                f.write(json.dumps(msg, default=str) + "\n")
        print(f"[transcript saved: {transcript_path}]")
        # Ask LLM to summarize
        conversation_text = json.dumps(self.messages, default=str)[:80000]
        response = self.call_llm(
            messages=[
                {
                    "role": "user",
                    "content": "Summarize this conversation for continuity. Include: "
                    "1) What was accomplished, 2) Current state, 3) Key decisions made. "
                    "Be concise but preserve critical details.\n\n" + conversation_text,
                }
            ],
        )
        summary = response.choices[0].message.content
        # Replace all messages with compressed summary
        self.messages = [
            {"role": "system", "content": self.messages[0]["content"]},
            {
                "role": "user",
                "content": f"[Conversation compressed. Transcript: {transcript_path}]\n\n{summary}",
            },
            {
                "role": "assistant",
                "content": "Understood. I have the context from the summary. Continuing.",
            },
        ]
        return

    def estimate_tokens(self) -> int:
        """Rough token count: ~4 chars per token."""
        return len(str(self.messages)) // 4

    def handle_tool_calls(self, msg):
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = self.use_tool(tc.function.name, args)
                self.append_tool_response(tc.id, result)
