from client import client
from tool import tools
from skill import skill
import time
import json
from log import logger
from pathlib import Path

WORKDIR = Path.cwd()

MAIN_AGENT_SYSTEM = f"""
You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
Use the task tool to delegate exploration or subtasks."""

SUB_AGENT_SYSTEM = f"""You are a coding agent at {WORKDIR}.
You will be given a prompt from the main agent, and you should respond with a final answer.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.
Skills available:
{skill.get_descriptions()}.
"""

TRANSCRIPT_DIR = WORKDIR / ".transcripts"


class Agent:
    def __init__(
        self,
        model="doubao-seed-2-0-lite-260215",
        max_tokens=8000,
        n=1,
        system=MAIN_AGENT_SYSTEM,
        tools=tools,
        client=client,
        sub_agent=None,
        name="mainAgent",
        logger=logger,
        transcript_dir=TRANSCRIPT_DIR,
        max_context_tokens=1600,
    ):
        self.model = model
        self.tools = tools
        self.max_tokens = max_tokens
        self.n = n
        self.messages = [{"role": "system", "content": system}]
        self.client = client
        self.sub_agent = sub_agent
        self.name = name
        self.logger = logger
        self.transcript_dir = transcript_dir
        self.max_context_tokens = max_context_tokens

    def run_loop(self):
        while True:
            if self.estimate_tokens() > self.max_context_tokens:
                self.auto_compact()
            self.log_messages()
            response = self.call_llm(self.messages)
            self.log_response(response)
            choice = response.choices[0]
            msg = choice.message
            # append the assistant message to the conversation, including any tool calls or refusals
            self.append_assistant_message(msg.content)

            if choice.finish_reason != "tool_calls":
                break

            # need to run the tool calls and append the results to the conversation before the next turn
            for tc in msg.tool_calls:
                if tc.function.name == "task_tool" and self.sub_agent:
                    args = json.loads(tc.function.arguments)
                    prompt = args["prompt"]
                    self.sub_agent.append_user_message(prompt)
                    self.sub_agent.run_loop()
                    sub_result = self.sub_agent.final_response()
                    self.append_tool_response(tc.id, sub_result)
                    self.sub_agent.re_init_messages(SUB_AGENT_SYSTEM)
                    continue

                args = json.loads(tc.function.arguments)
                result = self.use_tool(tc.function.name, args)
                self.append_tool_response(tc.id, result)

    def final_response(self) -> str:
        return self.messages[-1]["content"] if self.messages else ""

    def append_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def use_tool(self, name: str, args: dict) -> str:
        try:
            result = self.tools.dispatch(name, args)
            return result
        except Exception as e:
            return f"Error using tool '{name}': {str(e)}"

    def call_llm(self, messages=None):
        if messages is None:
            return
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools.tools,
            max_tokens=self.max_tokens,
            n=self.n,
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

    def re_init_messages(self, system):
        self.messages = [{"role": "system", "content": system}]

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


subAgent = Agent(system=SUB_AGENT_SYSTEM, tools=tools, client=client, name="subAgent")
mainAgent = Agent(
    system=MAIN_AGENT_SYSTEM,
    tools=tools,
    client=client,
    sub_agent=subAgent,
    name="mainAgent",
)
