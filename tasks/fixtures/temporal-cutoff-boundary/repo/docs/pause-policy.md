# Billing Pause Effective-Date Policy

Pause requests are evaluated in the account's local timezone.

Rules:

1. Convert `requested_at` to `account_timezone` before applying any date or hour logic.
2. Requests before 17:00 local time take effect on the local request date.
3. Requests at exactly 17:00 local time or later take effect on the next business day.
4. Saturdays and Sundays are not business days. If a calculated effective date lands on a weekend, roll it forward to Monday.
5. The returned reason must explain whether the request was before cutoff, at or after cutoff, or received on a weekend.

Do not use the UTC calendar date unless the account timezone is UTC.
