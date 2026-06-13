class StubCommandParser:
    def __init__(self):
        self.queue, self.calls = [], []
        self.extract_result = None      # ExpenseExtraction | ParserFailure
        self.last_image_url: str | None = None
    def queue_command(self, cmd): self.queue.append(cmd); return self
    def parse_user_command(self, context, message):
        self.calls.append({"context": context, "message": message})
        assert self.queue, "StubCommandParser: queue empty but LLM was called"
        return self.queue.pop(0)

    def extract_expense(self, image_url: str):
        self.last_image_url = image_url
        assert self.extract_result is not None, "set stub_parser.extract_result in the test"
        return self.extract_result
