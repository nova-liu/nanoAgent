from client import client


class AgentContext:
    def __init__(
        self,
        name,
        role,
        messages=None,
        client=client,
    ):
        self.name = name
        self.role = role
        self.messages = messages or []
        self.client = client
