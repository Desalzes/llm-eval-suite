# Process Result Policy

The process boundary reports command execution with two independent signals:

- `timed_out`: whether the supervisor stopped waiting because the timeout was reached.
- `exit_code`: the process exit code if one was produced.

Classification rules:

1. If `timed_out` is true, classify the result as `timeout`.
   - Timeouts are retryable.
   - Severity is `transient`.
   - This rule wins even when `exit_code` is `0`, negative, or missing.
2. If `timed_out` is false and `exit_code` is `0`, classify the result as `success`.
   - Success is not retryable.
   - Severity is `ok`.
3. If `timed_out` is false and `exit_code` is anything other than `0`, classify the result as `command_failed`.
   - Command failures are not retryable by default.
   - Severity is `error`.
   - Negative exit codes are still command failures unless `timed_out` is true.

Messages should include the command and enough detail for an operator to tell what happened. For command failures, prefer the first non-empty line from stderr, then stdout. If no output exists, mention the exit code.
