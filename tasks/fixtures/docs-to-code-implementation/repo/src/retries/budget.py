from __future__ import annotations


class RetryBudget:
    """Tracks retry capacity for operations that use retry policies."""

    def __init__(self, max_retries: int) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.max_retries = max_retries
        self._remaining = max_retries

    @property
    def remaining(self) -> int:
        return self._remaining

    def try_consume(self) -> bool:
        if self._remaining <= 0:
            return False
        self._remaining -= 1
        return True

    def reset(self) -> None:
        self._remaining = self.max_retries

    def fork_for_operation(self) -> "RetryBudget":
        return RetryBudget(self.max_retries)
