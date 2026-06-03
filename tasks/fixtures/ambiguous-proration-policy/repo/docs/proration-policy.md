# Seat Change Proration Policy

This policy defines "fair proration" for mid-cycle subscription seat changes.

## Invoice Line Rules

- Seat increases during an active billing cycle are charged for remaining whole days only.
- The change day counts as a remaining day.
- The amount is `seat_delta * monthly_price_cents * remaining_days / billing_cycle_days`.
- Amounts are rounded to the nearest cent using half-up rounding.
- Seat decreases do not create an immediate customer credit. They produce a zero-amount line with reason `defer_to_renewal`.
- Trial accounts do not create mid-cycle charges. They produce a zero-amount line with reason `trial_no_charge`.
- The returned `quantity_delta` still records the signed seat change for audit purposes.
