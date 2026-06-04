# Batch Update Contract

Each update row may change an account email, status, or both.

Rules:

- Valid statuses are `active`, `paused`, and `closed`.
- An email must contain exactly one `@` and a non-empty local and domain part.
- A missing account produces `not_found`.
- An invalid email produces `invalid_email`.
- An invalid status produces `invalid_status`.
- A row with any invalid field must not mutate that account.
- Valid rows should still apply when other rows fail.
- Applied and failed lists should follow input order.
