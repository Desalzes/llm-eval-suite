from datetime import date

from subscriptions.grace_policy import PlanTier, RenewalState, classify_renewal_access


def _state(
    *,
    tier: PlanTier = PlanTier.STANDARD,
    due: date = date(2026, 5, 1),
    as_of: date = date(2026, 5, 1),
    paid: bool = False,
    manual_hold: bool = False,
) -> RenewalState:
    return RenewalState(
        account_id="acct_123",
        plan_tier=tier,
        invoice_due_date=due,
        as_of=as_of,
        invoice_paid=paid,
        manual_hold=manual_hold,
    )


def test_paid_invoice_is_active_and_billable() -> None:
    decision = classify_renewal_access(_state(as_of=date(2026, 6, 1), paid=True))

    assert decision.status == "active"
    assert decision.access_allowed is True
    assert decision.billable is True
    assert "paid" in decision.reason


def test_standard_account_suspends_after_three_calendar_days() -> None:
    inside = classify_renewal_access(_state(as_of=date(2026, 5, 4)))
    outside = classify_renewal_access(_state(as_of=date(2026, 5, 5)))

    assert inside.status == "active"
    assert inside.access_allowed is True
    assert outside.status == "suspended"
    assert outside.access_allowed is False
    assert outside.billable is False


def test_enterprise_account_keeps_access_through_ten_calendar_days() -> None:
    inside = classify_renewal_access(
        _state(tier=PlanTier.ENTERPRISE, as_of=date(2026, 5, 11))
    )
    outside = classify_renewal_access(
        _state(tier=PlanTier.ENTERPRISE, as_of=date(2026, 5, 12))
    )

    assert inside.status == "active"
    assert inside.access_allowed is True
    assert outside.status == "suspended"
    assert outside.access_allowed is False


def test_manual_hold_returns_manual_review_without_suspending() -> None:
    decision = classify_renewal_access(
        _state(as_of=date(2026, 8, 1), manual_hold=True)
    )

    assert decision.status == "manual_review"
    assert decision.access_allowed is True
    assert decision.billable is False
    assert "manual" in decision.reason.lower()


def test_standard_and_enterprise_boundaries_are_not_collapsed() -> None:
    standard = classify_renewal_access(
        _state(tier=PlanTier.STANDARD, as_of=date(2026, 5, 8))
    )
    enterprise = classify_renewal_access(
        _state(tier=PlanTier.ENTERPRISE, as_of=date(2026, 5, 8))
    )

    assert standard.status == "suspended"
    assert enterprise.status == "active"
