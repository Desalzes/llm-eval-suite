from __future__ import annotations

import httpx
import pytest

from fakes.fake_transport import (
    FakeNotificationTransport,
    notification_response,
    request_json,
    service_error,
)
from notifications.client import NotificationDeliveryError, NotificationsClient
from notifications.retries import RetryPolicy


def build_client(
    transport: FakeNotificationTransport,
    *,
    delays: list[float] | None = None,
    max_attempts: int = 3,
    backoff_seconds: tuple[float, ...] = (0.25, 0.5),
) -> NotificationsClient:
    return NotificationsClient(
        "https://notify.example.test",
        "test-api-key",
        transport=transport,
        retry_policy=RetryPolicy(
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
        ),
        sleep=(delays if delays is not None else []).append,
    )


def test_send_notification_preserves_public_result_shape_and_request_contract() -> None:
    transport = FakeNotificationTransport(
        [
            notification_response(
                notification_id="ntf_welcome",
                recipient="ops@example.com",
                status="queued",
            )
        ]
    )
    client = build_client(transport)

    result = client.send_notification(
        "ops@example.com",
        "Deploy complete",
        "The production deploy finished.",
        metadata={"service": "billing"},
    )

    assert result == {
        "notification_id": "ntf_welcome",
        "status": "queued",
        "recipient": "ops@example.com",
        "attempts": 1,
    }
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.method == "POST"
    assert request.url == "https://notify.example.test/v1/notifications"
    assert request.headers["authorization"] == "Bearer test-api-key"
    assert request_json(request) == {
        "recipient": "ops@example.com",
        "subject": "Deploy complete",
        "body": "The production deploy finished.",
        "metadata": {"service": "billing"},
    }


def test_retryable_status_uses_backoff_and_reports_attempt_count() -> None:
    delays: list[float] = []
    transport = FakeNotificationTransport(
        [
            service_error(503, "temporarily overloaded"),
            notification_response(notification_id="ntf_retry", status="accepted"),
        ]
    )
    client = build_client(transport, delays=delays)

    result = client.send_notification(
        "ops@example.com",
        "Queue lag",
        "The notification worker is catching up.",
    )

    assert result == {
        "notification_id": "ntf_retry",
        "status": "accepted",
        "recipient": "ops@example.com",
        "attempts": 2,
    }
    assert delays == [0.25]
    assert len(transport.requests) == 2


def test_retryable_transport_error_replays_request_with_next_backoff() -> None:
    delays: list[float] = []
    transport = FakeNotificationTransport(
        [
            httpx.ConnectTimeout("connect timed out"),
            httpx.ReadTimeout("read timed out"),
            notification_response(notification_id="ntf_transport_retry"),
        ]
    )
    client = build_client(transport, delays=delays)

    result = client.send_notification(
        "ops@example.com",
        "Status page",
        "Posting status update.",
    )

    assert result["notification_id"] == "ntf_transport_retry"
    assert result["attempts"] == 3
    assert delays == [0.25, 0.5]
    assert len(transport.requests) == 3


def test_retry_exhaustion_raises_delivery_error_with_last_status_and_attempts() -> None:
    delays: list[float] = []
    transport = FakeNotificationTransport(
        [
            service_error(503, "first failure"),
            service_error(503, "second failure"),
        ]
    )
    client = build_client(
        transport,
        delays=delays,
        max_attempts=2,
        backoff_seconds=(0.1,),
    )

    with pytest.raises(NotificationDeliveryError) as exc_info:
        client.send_notification(
            "ops@example.com",
            "Incident",
            "Escalation failed.",
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.attempts == 2
    assert delays == [0.1]
    assert len(transport.requests) == 2


def test_non_retryable_status_is_not_retried() -> None:
    delays: list[float] = []
    transport = FakeNotificationTransport([service_error(400, "bad recipient")])
    client = build_client(transport, delays=delays)

    with pytest.raises(NotificationDeliveryError) as exc_info:
        client.send_notification(
            "not-an-email",
            "Welcome",
            "Hello",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.attempts == 1
    assert delays == []
    assert len(transport.requests) == 1
