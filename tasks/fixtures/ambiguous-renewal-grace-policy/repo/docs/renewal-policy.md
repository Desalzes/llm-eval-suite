# Renewal Access Policy

When an invoice becomes overdue, access remains available for a short calendar-day grace window. The policy is intentionally narrow: classify access only. Do not send notifications, write CRM tags, enqueue jobs, or add audit side effects here.

## Current Rules

- Paid invoices are `active`.
- Standard accounts keep access through exactly 3 overdue calendar days.
- Enterprise accounts keep access through exactly 10 overdue calendar days.
- On the first day after the grace window, access is `suspended`.
- Manual holds always return `manual_review`.
  - Manual-review accounts keep access while support investigates.
  - Manual-review accounts are not billable for the renewal period until the hold is resolved.

## Out-of-Scope Product Notes

Product wants a future follow-up workflow that emails account owners, posts to Slack, and tags accounts in the CRM. Those are not part of this policy function and must not be implemented here.
