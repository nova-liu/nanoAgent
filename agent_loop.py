from client import client
from tool_calls import TOOLS, run_tool
from log import log_message, log_input
import os
import json

WORKING_DIR = os.getcwd()

SYSTEM = f"""You are a coding agent at {WORKING_DIR}. Use the task tool to delegate exploration or subtasks."""


def agent_loop(messages):
    while True:
        log_input(messages)
        response = client.chat.completions.create(
            model="doubao-seed-2-0-lite-260215",
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
            n=1,
        )
        choice = response.choices[0]
        msg = choice.message
        log_message(msg)

        # append the assistant message to the conversation, including any tool calls or refusals
        messages.append({"role": msg.role, "content": msg.content})

        if choice.finish_reason != "tool_calls":
            break

        # need to run the tool calls and append the results to the conversation before the next turn
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = run_tool(tc.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
