from client import client
from tool import tools
from skill import skill
import time
import json
from log import logger
from pathlib import Path
import threading
from config import WORKDIR, TRANSCRIPT_DIR, TEAM_DIR
from message_bus import message_bus

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


class Agent:
    def __init__(
        self,
        model="doubao-seed-1-8-251228",
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
        team_dir=TEAM_DIR,
        role="leader",
        message_bus=message_bus,
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
        self.team_dir = team_dir
        self.team_dir.mkdir(exist_ok=True)
        self.team_config_path = self.team_dir / "config.json"
        self.team_config = self._load_team_config()
        self.threads = {}
        self.role = role
        self.message_bus = message_bus

    def _load_team_config(self) -> dict:
        if self.team_config_path.exists():
            return json.loads(self.team_config_path.read_text())
        return {"team_name": "default", "members": []}

    def _save_team_config(self):
        self.team_config_path.write_text(json.dumps(self.team_config, indent=2))

    def _find_member(self, name: str) -> dict:
        for m in self.team_config["members"]:
            if m["name"] == name:
                return m
        return None

    def spawn(self, name: str, role: str) -> str:
        member = self._find_member(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.team_config["members"].append(member)
        self._save_team_config()

        agent = Agent(
            model=self.model,
            tools=self.tools,
            client=self.client,
            name=name,
            logger=self.logger,
            role=role,
        )

        thread = threading.Thread(
            target=agent.run_loop,
            args=(),
            daemon=True,
        )

        self.threads[name] = thread
        thread.start()
        return f"Spawned '{name}' (role: {role})"

    def list_team_all(self) -> str:
        if not self.team_config["members"]:
            return "No teammates."
        lines = [f"Team: {self.team_config['team_name']}"]
        for m in self.team_config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.team_config["members"]]

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
            response = self.call_llm(self.messages)
            self.log_response(response)

            msg = response.choices[0].message
            # append the assistant message to the conversation, including any tool calls or refusals
            self.append_assistant_message(msg.content)

            # need to run the tool calls and append the results to the conversation before the next turn
            self.handle_tool_calls(msg)

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

    def handle_tool_calls(self, msg):
        if msg.tool_calls:
            for tc in msg.tool_calls:
                if self.delegate_by_agent(tc.function.name):
                    result = self.handle_delegation(
                        tc.function.name, json.loads(tc.function.arguments)
                    )
                    self.append_tool_response(tc.id, result)
                    continue
                args = json.loads(tc.function.arguments)
                result = self.use_tool(tc.function.name, args)
                self.append_tool_response(tc.id, result)

    def clear_notifications(self):
        notifs = self.tools.BG.drain_notifications()
        if notifs and self.messages:
            notif_text = "\n".join(
                f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs
            )
            self.messages.append(
                {
                    "role": "user",
                    "content": f"<background-results>\n{notif_text}\n</background-results>",
                }
            )

    def delegate_by_agent(self, tool_name: str) -> bool:
        if tool_name in ["sub_agent_tool", "compact", "list_team_all", "spawn"]:
            return True
        return False

    def handle_delegation(self, tool_name: str, args: dict) -> str:
        if tool_name == "sub_agent_tool" and self.sub_agent:
            prompt = args["prompt"]
            self.sub_agent.append_user_message(prompt)
            self.sub_agent.run_loop()
            sub_result = self.sub_agent.final_response()
            self.sub_agent.re_init_messages(SUB_AGENT_SYSTEM)
            return sub_result
        elif tool_name == "compact":
            self.auto_compact()
            return "Context compacted."
        elif tool_name == "list_team_all":
            return self.list_team_all()
        elif tool_name == "spawn":
            return self.spawn(args["name"], args["role"])
        else:
            return f"Unknown delegation for tool '{tool_name}'"


subAgent = Agent(system=SUB_AGENT_SYSTEM, tools=tools, client=client, name="subAgent")
mainAgent = Agent(
    system=MAIN_AGENT_SYSTEM,
    tools=tools,
    client=client,
    sub_agent=subAgent,
    name="mainAgent",
)
