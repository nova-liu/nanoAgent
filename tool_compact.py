from tool import Tool
from config import TRANSCRIPT_DIR
import time, json
from agent_context import AgentContext

NAME = "compact"
compact_tool = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Compact the conversation history to reduce token usage. This can be done by summarizing earlier messages or removing less relevant ones.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


def compact(agent_context: AgentContext) -> str:
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in agent_context.messages:
            f.write(json.dumps(msg, default=str) + "\n")
    print(f"[transcript saved: {transcript_path}]")
    # Ask LLM to summarize
    conversation_text = json.dumps(agent_context.messages, default=str)[:80000]
    messages = [
        {
            "role": "user",
            "content": "Summarize this conversation for continuity. Include: "
            "1) What was accomplished, 2) Current state, 3) Key decisions made. "
            "Be concise but preserve critical details.\n\n" + conversation_text,
        }
    ]
    response = agent_context.client.chat.completions.create(
        model=agent_context.model,
        messages=messages,
        max_tokens=agent_context.max_tokens,
        n=1,
    )

    summary = response.choices[0].message.content
    # Replace all messages with compressed summary
    agent_context.messages = [
        {"role": "system", "content": agent_context.messages[0]["content"]},
        {
            "role": "user",
            "content": f"[Conversation compressed. Transcript: {transcript_path}]\n\n{summary}",
        },
        {
            "role": "assistant",
            "content": "Understood. I have the context from the summary. Continuing.",
        },
    ]
    return "Conversation history compacted to reduce token usage."


compact_tool_instance = Tool(name=NAME, content=compact_tool, function=compact)
