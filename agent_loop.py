from client import client
from tool_calls import TOOLS, run_tool
from log import log_message, log_input
import os
import json

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."


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
        messages.append(extract_assistant_message(msg))

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


def extract_assistant_message(msg) -> dict:
    assistant_message = {
        "role": "assistant",
    }

    if msg.content is not None:
        assistant_message["content"] = msg.content

    if msg.refusal is not None:
        assistant_message["refusal"] = msg.refusal

    if msg.tool_calls is not None:
        assistant_message["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return assistant_message
