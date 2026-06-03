import pytest

from integrations.failure_classification import ProviderError, classify_sync_failure


def valid_payload() -> dict[str, object]:
    return {
        "account_id": "acct_123",
        "external_id": "evt_456",
        "event_type": "invoice.created",
    }


def test_missing_payload_fields_are_invalid_request_even_when_provider_rejects() -> None:
    result = classify_sync_failure(
        {"account_id": "", "event_type": "invoice.created"},
        ProviderError(status_code=400, message="external id is required"),
    )

    assert result.category == "invalid_request"
    assert result.retryable is False
    assert result.action == "fix_payload"
    assert result.reason == "missing required fields: account_id, external_id"
    assert result.delay_seconds is None


@pytest.mark.parametrize("status_code", [401, 403])
def test_auth_failures_require_credential_refresh(status_code: int) -> None:
    result = classify_sync_failure(
        valid_payload(),
        ProviderError(status_code=status_code, message="token expired"),
    )

    assert result.category == "auth"
    assert result.retryable is False
    assert result.action == "refresh_credentials"
    assert str(status_code) in result.reason
    assert result.delay_seconds is None


def test_rate_limit_uses_retry_after_delay() -> None:
    result = classify_sync_failure(
        valid_payload(),
        ProviderError(status_code=429, message="too many requests", headers={"Retry-After": "45"}),
    )

    assert result.category == "rate_limited"
    assert result.retryable is True
    assert result.action == "retry_after_delay"
    assert result.reason == "provider returned 429 rate limit"
    assert result.delay_seconds == 45


def test_rate_limit_defaults_to_sixty_seconds_when_header_is_missing() -> None:
    result = classify_sync_failure(
        valid_payload(),
        ProviderError(status_code=429, message="too many requests"),
    )

    assert result.category == "rate_limited"
    assert result.retryable is True
    assert result.action == "retry_after_delay"
    assert result.delay_seconds == 60


@pytest.mark.parametrize(
    "error",
    [
        ProviderError(timeout=True, message="request timed out"),
        ProviderError(status_code=502, message="bad gateway"),
        ProviderError(status_code=503, message="service unavailable"),
        ProviderError(status_code=504, message="gateway timeout"),
    ],
)
def test_provider_outages_are_retryable_without_losing_the_outage_category(
    error: ProviderError,
) -> None:
    result = classify_sync_failure(valid_payload(), error)

    assert result.category == "provider_outage"
    assert result.retryable is True
    assert result.action == "retry"
    assert result.delay_seconds is None


def test_other_server_errors_remain_generic_provider_errors() -> None:
    result = classify_sync_failure(
        valid_payload(),
        ProviderError(status_code=500, message="internal server error"),
    )

    assert result.category == "provider_error"
    assert result.retryable is True
    assert result.action == "retry"
    assert result.reason == "provider returned 500"


def test_unrecognized_failures_are_not_retried_blindly() -> None:
    result = classify_sync_failure(
        valid_payload(),
        ProviderError(status_code=418, message="unexpected response"),
    )

    assert result.category == "unknown"
    assert result.retryable is False
    assert result.action == "escalate"
    assert result.reason == "unclassified provider response: 418"
