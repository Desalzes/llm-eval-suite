# Review Feedback

The reviewer left three comments on the refund-policy change. Only the first one is blocking for this task.

## Blocking

Fraud-review orders must not issue an automatic card refund. The current implementation treats `reason="fraud_review"` like a normal cancellation and sends money back immediately. That can hide risk before the fraud team has reviewed the order. Instead, return a zero-amount plan with:

- `customer_action`: `manual_review`
- `accounting_code`: `fraud_hold`
- `note`: include the order id and say that fraud review is required

## Naming Nit

The local variable named `gross` could be renamed to `gross_cents` someday, but this is not required for this task.

## Product Suggestion

It might be useful to notify Slack when a fraud hold is created. That is out of scope here because this package should stay a pure policy library.
