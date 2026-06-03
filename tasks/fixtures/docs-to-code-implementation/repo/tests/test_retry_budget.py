from __future__ import annotations

import pytest

from retries.budget import RetryBudget
from retries.client import RetryClient
from retries.policy import RetryPolicy


class TransientFailure(Exception):
    pass


class ScriptedOperation:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> object:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def policy_with_budget(max_retries: int, *, max_attempts: int) -> RetryPolicy:
    return RetryPolicy.standard(
        budget=RetryBudget(max_retries=max_retries),
        max_attempts=max_attempts,
        retry_exceptions=(TransientFailure,),
    )


def test_retry_budget_is_shared_across_operations_until_explicit_reset() -> None:
    events: list[dict[str, object]] = []
    policy = policy_with_budget(max_retries=2, max_attempts=4)
    client = RetryClient(policy, telemetry=events.append)
    first = ScriptedOperation(
        [
            TransientFailure("alpha first failure"),
            TransientFailure("alpha second failure"),
            "alpha accepted",
        ]
    )
    second = ScriptedOperation(
        [
            TransientFailure("beta first failure"),
            "beta would have succeeded if retried",
        ]
    )

    assert client.run(first, operation_name="alpha") == "alpha accepted"

    with pytest.raises(TransientFailure, match="beta first failure"):
        client.run(second, operation_name="beta")

    assert first.calls == 3
    assert second.calls == 1
    assert policy.budget.remaining == 0
    assert events[-1] == {
        "event": "retry.skipped",
        "operation": "beta",
        "policy": "standard",
        "attempt": 1,
        "reason": "TransientFailure",
        "cause": "retry_budget_exhausted",
        "budget_remaining": 0,
    }


def test_retry_attempt_limit_resets_per_operation_but_budget_does_not() -> None:
    events: list[dict[str, object]] = []
    policy = policy_with_budget(max_retries=4, max_attempts=3)
    client = RetryClient(policy, telemetry=events.append)
    first = ScriptedOperation(
        [
            TransientFailure("first operation attempt one"),
            TransientFailure("first operation attempt two"),
            "first synced",
        ]
    )
    second = ScriptedOperation(
        [
            TransientFailure("second operation attempt one"),
            TransientFailure("second operation attempt two"),
            "second synced",
        ]
    )

    assert client.run(first, operation_name="first-sync") == "first synced"
    assert client.run(second, operation_name="second-sync") == "second synced"

    scheduled = [event for event in events if event["event"] == "retry.scheduled"]
    assert [
        (event["operation"], event["attempt"], event["budget_remaining"])
        for event in scheduled
    ] == [
        ("first-sync", 1, 3),
        ("first-sync", 2, 2),
        ("second-sync", 1, 1),
        ("second-sync", 2, 0),
    ]
    assert policy.budget.remaining == 0


def test_telemetry_labels_match_documented_retry_schema() -> None:
    events: list[dict[str, object]] = []
    policy = policy_with_budget(max_retries=1, max_attempts=3)
    client = RetryClient(policy, telemetry=events.append)
    operation = ScriptedOperation(
        [
            TransientFailure("temporary checkout failure"),
            "checkout complete",
        ]
    )

    assert client.run(operation, operation_name="checkout") == "checkout complete"

    assert events == [
        {
            "event": "retry.scheduled",
            "operation": "checkout",
            "policy": "standard",
            "attempt": 1,
            "reason": "TransientFailure",
            "budget_remaining": 0,
        }
    ]


def test_budget_exhaustion_telemetry_uses_documented_labels() -> None:
    events: list[dict[str, object]] = []
    policy = policy_with_budget(max_retries=0, max_attempts=3)
    client = RetryClient(policy, telemetry=events.append)
    operation = ScriptedOperation(
        [
            TransientFailure("no retry tokens left"),
            "should not be called",
        ]
    )

    with pytest.raises(TransientFailure, match="no retry tokens left"):
        client.run(operation, operation_name="checkout")

    assert operation.calls == 1
    assert events == [
        {
            "event": "retry.skipped",
            "operation": "checkout",
            "policy": "standard",
            "attempt": 1,
            "reason": "TransientFailure",
            "cause": "retry_budget_exhausted",
            "budget_remaining": 0,
        }
    ]


def test_public_policy_names_are_stable() -> None:
    assert RetryPolicy.standard().name == "standard"
    assert RetryPolicy.conservative().name == "conservative"
