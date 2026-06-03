from __future__ import annotations

import json
from typing import Any

import httpx


class FakeNotificationTransport(httpx.BaseTransport):
    def __init__(self, outcomes: list[httpx.Response | BaseException]) -> None:
        self._outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._outcomes:
            raise AssertionError("fake transport received an unexpected request")

        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def notification_response(
    *,
    notification_id: str = "ntf_123",
    recipient: str = "ops@example.com",
    status: str = "queued",
    status_code: int = 202,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "data": {
                "id": notification_id,
                "recipient": recipient,
                "status": status,
            }
        },
    )


def service_error(status_code: int, message: str) -> httpx.Response:
    return httpx.Response(status_code, json={"error": {"message": message}})


def request_json(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content.decode("utf-8"))
