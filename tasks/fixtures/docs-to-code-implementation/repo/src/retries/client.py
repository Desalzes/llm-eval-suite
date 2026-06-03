from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from .policy import RetryPolicy

T = TypeVar("T")
Telemetry = Callable[[dict[str, object]], None]


class RetryClient:
    """Runs operations with a retry policy."""

    def __init__(self, policy: RetryPolicy, telemetry: Telemetry | None = None) -> None:
        self.policy = policy
        self.telemetry = telemetry
        self._retry_attempts = 0

    def run(self, operation: Callable[[], T], *, operation_name: str) -> T:
        operation_budget = self.policy.budget.fork_for_operation()

        while True:
            try:
                return operation()
            except BaseException as error:
                self._retry_attempts += 1
                if not self.policy.can_retry(error, self._retry_attempts):
                    raise
                if not operation_budget.try_consume():
                    self._emit(
                        {
                            "event": "retry.skipped",
                            "operation_name": operation_name,
                            "attempt_number": self._retry_attempts,
                            "error": type(error).__name__,
                            "remaining": operation_budget.remaining,
                        }
                    )
                    raise
                self._emit(
                    {
                        "event": "retry",
                        "operation_name": operation_name,
                        "attempt_number": self._retry_attempts,
                        "error": type(error).__name__,
                        "remaining": operation_budget.remaining,
                    }
                )

    def _emit(self, event: dict[str, object]) -> None:
        if self.telemetry is not None:
            self.telemetry(event)
