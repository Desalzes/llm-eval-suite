from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


REQUIRED_FIELDS = ("account_id", "external_id", "event_type")


@dataclass(frozen=True)
class ProviderError(Exception):
    status_code: int | None = None
    message: str = ""
    headers: Mapping[str, str] = field(default_factory=dict)
    timeout: bool = False


@dataclass(frozen=True)
class FailureClassification:
    category: str
    retryable: bool
    action: str
    reason: str
    delay_seconds: int | None = None


def classify_sync_failure(
    payload: Mapping[str, object], error: ProviderError | None
) -> FailureClassification:
    missing = [field for field in REQUIRED_FIELDS if not payload.get(field)]

    if error is not None:
        if error.timeout:
            return FailureClassification(
                category="provider_outage",
                retryable=True,
                action="retry",
                reason="provider request timed out",
            )
        if error.status_code is not None and error.status_code >= 400:
            return FailureClassification(
                category="provider_error",
                retryable=True,
                action="retry",
                reason=f"provider returned {error.status_code}",
            )

    if missing:
        return FailureClassification(
            category="invalid_request",
            retryable=False,
            action="fix_payload",
            reason=f"missing required fields: {', '.join(missing)}",
        )

    return FailureClassification(
        category="unknown",
        retryable=False,
        action="escalate",
        reason="unclassified failure",
    )
