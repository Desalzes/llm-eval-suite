from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .budget import RetryBudget

ExceptionTypes: TypeAlias = tuple[type[BaseException], ...]


@dataclass
class RetryPolicy:
    """Configuration for deciding whether failed operations can be retried."""

    name: str
    max_attempts: int
    budget: RetryBudget
    retry_exceptions: ExceptionTypes

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

    @classmethod
    def standard(
        cls,
        *,
        budget: RetryBudget | None = None,
        max_attempts: int = 3,
        retry_exceptions: ExceptionTypes = (TimeoutError, ConnectionError),
    ) -> "RetryPolicy":
        return cls(
            name="standard",
            max_attempts=max_attempts,
            budget=budget or RetryBudget(max_retries=3),
            retry_exceptions=retry_exceptions,
        )

    @classmethod
    def conservative(
        cls,
        *,
        budget: RetryBudget | None = None,
        max_attempts: int = 2,
        retry_exceptions: ExceptionTypes = (TimeoutError, ConnectionError),
    ) -> "RetryPolicy":
        return cls(
            name="conservative",
            max_attempts=max_attempts,
            budget=budget or RetryBudget(max_retries=1),
            retry_exceptions=retry_exceptions,
        )

    def is_retryable(self, error: BaseException) -> bool:
        return isinstance(error, self.retry_exceptions)

    def can_retry(self, error: BaseException, retry_attempt: int) -> bool:
        return self.is_retryable(error) and retry_attempt < self.max_attempts
