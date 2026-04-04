from client import client


class AgentContext:
    def __init__(
        self,
        name,
        role,
        system_template="Your name is {name} and your role is {role}.",
        model="doubao-seed-1-8-251228",
        client=client,
        max_tokens=8000,
        max_context_tokens=1600,
    ):
        self.name = name
        self.role = role
        self.messages = [
            {"role": "system", "content": system_template.format(name=name, role=role)}
        ]
        self.model = model
        self.max_tokens = max_tokens
        self.client = client
        self.max_context_tokens = max_context_tokens
