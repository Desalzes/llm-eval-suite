from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessResult:
    command: str
    exit_code: int | None
    timed_out: bool
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class FailureSummary:
    category: str
    retryable: bool
    severity: str
    message: str


def _first_line(text: str) -> str:
    for line in text.splitlines():
        clean = line.strip()
        if clean:
            return clean
    return ""


def summarize_process_result(result: ProcessResult) -> FailureSummary:
    if result.exit_code == 0:
        return FailureSummary(
            category="success",
            retryable=False,
            severity="ok",
            message=f"{result.command} completed successfully.",
        )

    if result.exit_code is not None and result.exit_code < 0:
        return FailureSummary(
            category="timeout",
            retryable=True,
            severity="transient",
            message=f"{result.command} timed out.",
        )

    detail = _first_line(result.stderr) or _first_line(result.stdout)
    if not detail:
        detail = f"exit code {result.exit_code}"

    return FailureSummary(
        category="command_failed",
        retryable=True,
        severity="error",
        message=f"{result.command} failed: {detail}",
    )
