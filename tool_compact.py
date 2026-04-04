from tool import Tool

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


def compact():
    # This is a placeholder for the actual compaction logic, which could involve summarizing or pruning messages.
    return "Conversation history compacted to reduce token usage."


compact_tool_instance = Tool(name=NAME, content=compact_tool, function=compact)
