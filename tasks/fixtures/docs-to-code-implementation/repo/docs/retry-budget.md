# Retry Budget Design

This document is the source of truth for the retry package. Tests and client
behavior must follow this document, even when existing code appears to imply a
different model.

## Definitions

A retry budget limits retry attempts, not first attempts. The first call for an
operation is always allowed and never consumes budget. Each later call caused by
a retry consumes one token before the retry is scheduled.

An operation is one call to `RetryClient.run`. Operation names are caller-supplied
labels used only for telemetry. They do not create separate budgets.

The retry attempt ordinal is scoped to one operation. The first retry inside an
operation is attempt `1`, the second retry is attempt `2`, and so on. Attempt
ordinals reset on every `RetryClient.run` call.

## Budget Lifetime

`RetryBudget` is mutable state. A `RetryPolicy` holds a reference to a budget,
and every `RetryClient` using that policy consumes from the same budget object.
Do not clone, fork, or reset a budget when an operation starts. The only supported
way to refill a budget is calling `RetryBudget.reset()` explicitly.

Budget exhaustion is checked after an operation fails with a retryable exception
and before the next attempt is called. If the budget is exhausted, the client
must re-raise the original exception and must not call the operation again.

## Per-Operation Attempt Limit

`RetryPolicy.max_attempts` includes the first attempt. A policy with
`max_attempts=3` allows one first attempt and up to two retries for each operation.
This limit resets for every call to `RetryClient.run`.

The per-operation attempt limit is independent from the shared retry budget:
operation-local retry ordinals reset, but the budget tokens do not reset.

If an operation reaches the per-operation attempt limit, the client must re-raise
the original exception. This does not consume an extra budget token because no
retry is scheduled.

## Retryable Exceptions

`RetryPolicy.retry_exceptions` is a tuple of exception classes. Only exceptions
matching that tuple are retryable. Non-retryable exceptions are raised
immediately without consuming budget and without emitting retry telemetry.

## Public Policy Names

Policy names are public telemetry values and must remain stable.

- `RetryPolicy.standard(...).name` is `"standard"`.
- `RetryPolicy.conservative(...).name` is `"conservative"`.

Callers may construct `RetryPolicy` directly with a custom name, but built-in
policy names must not be changed.

## Telemetry

Telemetry is optional. When supplied, it is a callable that accepts one dictionary.
The client emits telemetry only for retry decisions.

When a retry is scheduled, emit exactly these labels:

```python
{
    "event": "retry.scheduled",
    "operation": operation_name,
    "policy": policy.name,
    "attempt": retry_attempt_ordinal,
    "reason": exception_class_name,
    "budget_remaining": remaining_budget_after_consuming,
}
```

When a retryable exception cannot be retried because the shared budget is
exhausted, emit exactly these labels:

```python
{
    "event": "retry.skipped",
    "operation": operation_name,
    "policy": policy.name,
    "attempt": retry_attempt_ordinal_that_would_have_run,
    "reason": exception_class_name,
    "cause": "retry_budget_exhausted",
    "budget_remaining": 0,
}
```

No other key names are part of the telemetry contract for these events. In
particular, do not rename `operation`, `policy`, `attempt`, `reason`, or
`budget_remaining`.

## Example

Given one shared budget with two retry tokens and a standard policy with
`max_attempts=4`:

1. Operation `alpha` fails twice, then succeeds.
2. The first failure emits `retry.scheduled` with `attempt=1` and
   `budget_remaining=1`.
3. The second failure emits `retry.scheduled` with `attempt=2` and
   `budget_remaining=0`.
4. Operation `beta` fails once.
5. The beta failure emits `retry.skipped` with `attempt=1`, `cause` set to
   `"retry_budget_exhausted"`, and `budget_remaining=0`.
6. Operation `beta` is not called a second time.
