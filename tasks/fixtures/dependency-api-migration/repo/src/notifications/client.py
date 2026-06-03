from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from .retries import RetryPolicy


class NotificationDeliveryError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        attempts: int = 1,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.attempts = attempts
        self.__cause__ = cause


class NotificationsClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        retry_policy: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            dispatch=transport,
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=5.0,
        )
        self._retry_policy = retry_policy or RetryPolicy()
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def send_notification(
        self,
        recipient: str,
        subject: str,
        body: str,
        *,
        metadata: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "metadata": dict(metadata or {}),
        }

        for attempt in range(1, self._retry_policy.max_attempts + 1):
            try:
                response = self._client.post("/v1/notifications", json=payload)
            except self._retry_policy.retry_exceptions as exc:
                if self._retry_policy.can_retry_after_attempt(attempt):
                    self._sleep(self._retry_policy.delay_for_attempt(attempt))
                    continue
                raise NotificationDeliveryError(
                    "notification transport failed",
                    attempts=attempt,
                    cause=exc,
                ) from exc

            if response.status_code == 202:
                data = response.json()["data"]
                return {
                    "notification_id": data["id"],
                    "status": data["status"],
                    "recipient": data["recipient"],
                    "attempts": attempt,
                }

            if (
                self._retry_policy.should_retry_status(response.status_code)
                and self._retry_policy.can_retry_after_attempt(attempt)
            ):
                self._sleep(self._retry_policy.delay_for_attempt(attempt))
                continue

            raise NotificationDeliveryError(
                f"notification service returned HTTP {response.status_code}",
                status_code=response.status_code,
                attempts=attempt,
            )

        raise AssertionError("retry loop exited unexpectedly")
