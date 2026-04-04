from agent_context import AgentContext


class Tool:
    def __init__(
        self,
        name: str = "toolName",
        content: dict = None,
        function: callable = None,
    ):
        self.name = name
        self.content = content
        self.function = function

    def do(self, agent_context: AgentContext, args: dict) -> str:
        return self.function(agent_context, **args)
