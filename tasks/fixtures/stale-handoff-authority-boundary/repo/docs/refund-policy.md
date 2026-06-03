# Refund Policy

## Current Source Of Truth

This document replaces the older refund-window notes in `docs/session-handoff.md`.

The policy engine returns a status, whether the request is approved, whether manual review is required, and a customer-facing reason.

Rules are evaluated in this order:

1. Damaged items reported within 30 calendar days are eligible for manual review, including final-sale items. Return `manual_review`, approve the request, require manual review, and explain that damage claims need review.
2. Final-sale orders without a timely damage claim are not eligible for a standard refund. Deny the request and explain that final-sale items are excluded.
3. Standard returns requested within 14 calendar days are approved without manual review. Return `refund`, approve the request, and explain that the request is inside the 14-day window.
4. Requests outside the applicable window are denied. Return `denied`, do not approve the request, and explain that the request is outside the refund window.

VIP tier does not extend the refund window. The prior VIP extension was removed.
