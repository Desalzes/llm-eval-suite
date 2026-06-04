class Projector:
    _seen = set()  # BUG: class-level set is shared across every instance.

    def __init__(self):
        self.total = 0

    def handle(self, event_id, amount):
        if event_id in self._seen:
            return
        self._seen.add(event_id)
        self.total += amount
