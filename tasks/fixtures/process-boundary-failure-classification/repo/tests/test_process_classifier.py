from processes.classifier import ProcessResult, summarize_process_result


def test_zero_exit_without_timeout_is_success() -> None:
    summary = summarize_process_result(
        ProcessResult(command="python -m pytest", exit_code=0, timed_out=False)
    )

    assert summary.category == "success"
    assert summary.retryable is False
    assert summary.severity == "ok"
    assert "completed successfully" in summary.message


def test_timeout_flag_wins_even_when_exit_code_is_zero() -> None:
    summary = summarize_process_result(
        ProcessResult(
            command="python slow_job.py",
            exit_code=0,
            timed_out=True,
            duration_seconds=30.0,
        )
    )

    assert summary.category == "timeout"
    assert summary.retryable is True
    assert summary.severity == "transient"
    assert "python slow_job.py" in summary.message
    assert "30" in summary.message


def test_timeout_flag_wins_when_exit_code_is_missing() -> None:
    summary = summarize_process_result(
        ProcessResult(command="deploy --wait", exit_code=None, timed_out=True)
    )

    assert summary.category == "timeout"
    assert summary.retryable is True
    assert summary.severity == "transient"


def test_negative_exit_without_timeout_is_command_failure() -> None:
    summary = summarize_process_result(
        ProcessResult(
            command="worker",
            exit_code=-9,
            timed_out=False,
            stderr="Killed by supervisor\n",
        )
    )

    assert summary.category == "command_failed"
    assert summary.retryable is False
    assert summary.severity == "error"
    assert "Killed by supervisor" in summary.message


def test_nonzero_exit_uses_stderr_detail_and_is_not_retryable() -> None:
    summary = summarize_process_result(
        ProcessResult(
            command="python sync.py",
            exit_code=2,
            timed_out=False,
            stdout="ignored detail\n",
            stderr="\nusage: missing --account\nextra detail\n",
        )
    )

    assert summary.category == "command_failed"
    assert summary.retryable is False
    assert summary.severity == "error"
    assert "usage: missing --account" in summary.message
    assert "ignored detail" not in summary.message
