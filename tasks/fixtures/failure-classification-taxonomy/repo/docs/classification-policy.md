# Sync Failure Classification Policy

Callers depend on `classify_sync_failure` to decide whether to retry, fix data, refresh credentials, or escalate.

Required payload fields are `account_id`, `external_id`, and `event_type`. Missing, blank, or `None` values are invalid requests. Payload validation takes precedence over provider response classification because retrying bad data only creates duplicate work. Invalid requests use:

- category: `invalid_request`
- retryable: `False`
- action: `fix_payload`
- reason: `missing required fields: <comma-separated field names>`

Provider responses are classified after payload validation:

- HTTP `401` or `403`: category `auth`, retryable `False`, action `refresh_credentials`
- HTTP `429`: category `rate_limited`, retryable `True`, action `retry_after_delay`; delay comes from the `Retry-After` header and defaults to 60 seconds
- timeout, HTTP `502`, HTTP `503`, or HTTP `504`: category `provider_outage`, retryable `True`, action `retry`
- any other HTTP `5xx`: category `provider_error`, retryable `True`, action `retry`
- anything else: category `unknown`, retryable `False`, action `escalate`
