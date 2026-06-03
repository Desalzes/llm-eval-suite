from datetime import UTC, datetime

from billing.pause_policy import PauseRequest, calculate_pause_effective_date


def test_before_cutoff_uses_account_local_date_not_utc_date() -> None:
    decision = calculate_pause_effective_date(
        PauseRequest(
            account_id="acct_la",
            requested_at=datetime(2026, 5, 13, 0, 30, tzinfo=UTC),
            account_timezone="America/Los_Angeles",
        )
    )

    assert decision.effective_date.isoformat() == "2026-05-12"
    assert "before cutoff" in decision.reason.lower()


def test_exact_cutoff_rolls_to_next_business_day() -> None:
    decision = calculate_pause_effective_date(
        PauseRequest(
            account_id="acct_cutoff",
            requested_at=datetime(2026, 5, 13, 0, 0, tzinfo=UTC),
            account_timezone="America/Los_Angeles",
        )
    )

    assert decision.effective_date.isoformat() == "2026-05-13"
    assert "at or after cutoff" in decision.reason.lower()


def test_after_cutoff_on_friday_rolls_to_monday() -> None:
    decision = calculate_pause_effective_date(
        PauseRequest(
            account_id="acct_weekend",
            requested_at=datetime(2026, 5, 15, 22, 30, tzinfo=UTC),
            account_timezone="UTC",
        )
    )

    assert decision.effective_date.isoformat() == "2026-05-18"
    assert "at or after cutoff" in decision.reason.lower()


def test_weekend_request_rolls_forward_to_monday() -> None:
    decision = calculate_pause_effective_date(
        PauseRequest(
            account_id="acct_saturday",
            requested_at=datetime(2026, 5, 16, 10, 0, tzinfo=UTC),
            account_timezone="UTC",
        )
    )

    assert decision.effective_date.isoformat() == "2026-05-18"
    assert "weekend" in decision.reason.lower()


def test_standard_utc_business_day_before_cutoff_stays_same_day() -> None:
    decision = calculate_pause_effective_date(
        PauseRequest(
            account_id="acct_utc",
            requested_at=datetime(2026, 5, 12, 16, 59, tzinfo=UTC),
            account_timezone="UTC",
        )
    )

    assert decision.effective_date.isoformat() == "2026-05-12"
    assert "before cutoff" in decision.reason.lower()
