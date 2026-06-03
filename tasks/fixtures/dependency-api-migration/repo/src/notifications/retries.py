from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: tuple[float, ...] = (0.1, 0.5)
    retry_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )
    retry_exceptions: tuple[type[Exception], ...] = (
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.RemoteProtocolError,
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if not self.backoff_seconds:
            raise ValueError("backoff_seconds must contain at least one delay")
        object.__setattr__(
            self,
            "backoff_seconds",
            tuple(float(delay) for delay in self.backoff_seconds),
        )

    def should_retry_status(self, status_code: int) -> bool:
        return status_code in self.retry_status_codes

    def can_retry_after_attempt(self, attempt: int) -> bool:
        return attempt < self.max_attempts

    def delay_for_attempt(self, attempt: int) -> float:
        index = min(attempt - 1, len(self.backoff_seconds) - 1)
        return self.backoff_seconds[index]
