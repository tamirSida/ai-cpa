class StubCommandParser:
    def __init__(self):
        self.queue, self.expense_queue, self.calls = [], [], []
    def queue_command(self, cmd): self.queue.append(cmd); return self
    def parse_user_command(self, context, message):
        self.calls.append({"context": context, "message": message})
        assert self.queue, "StubCommandParser: queue empty but LLM was called"
        return self.queue.pop(0)
    def extract_expense(self, image_url):
        assert self.expense_queue, "StubCommandParser: expense queue empty"
        return self.expense_queue.pop(0)
