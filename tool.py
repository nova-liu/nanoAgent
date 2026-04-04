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

    def do(self, args: dict) -> str:
        return self.function(**args)
