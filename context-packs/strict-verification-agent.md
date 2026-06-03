# Strict Verification Agent Context Pack

Use this pack when correctness and auditability matter more than speed.

## Rules

- Treat tests and allowed paths as hard constraints.
- Make the smallest change that satisfies the task.
- Run verification before finishing.
- If verification fails, inspect the failure and fix the root cause.
- Do not claim completion without evidence.

## Completion

Report:

- exact verification output summary
- changed files
- whether any requested constraint could not be met
