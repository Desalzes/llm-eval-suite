from billing.proration import invoice_line_for_seat_change


def test_seat_increase_charges_remaining_days_including_change_day() -> None:
    line = invoice_line_for_seat_change(
        account_id="acct-upgrade",
        old_seats=5,
        new_seats=8,
        monthly_price_cents=1200,
        change_day=10,
        billing_cycle_days=30,
    )

    assert line == {
        "account_id": "acct-upgrade",
        "quantity_delta": 3,
        "amount_cents": 2520,
        "reason": "prorated_upgrade",
    }


def test_half_cent_proration_rounds_half_up() -> None:
    line = invoice_line_for_seat_change(
        account_id="acct-rounding",
        old_seats=1,
        new_seats=2,
        monthly_price_cents=1001,
        change_day=16,
        billing_cycle_days=30,
    )

    assert line["amount_cents"] == 501
    assert line["reason"] == "prorated_upgrade"


def test_seat_decrease_is_deferred_to_renewal_without_credit() -> None:
    line = invoice_line_for_seat_change(
        account_id="acct-downgrade",
        old_seats=8,
        new_seats=5,
        monthly_price_cents=1200,
        change_day=10,
        billing_cycle_days=30,
    )

    assert line == {
        "account_id": "acct-downgrade",
        "quantity_delta": -3,
        "amount_cents": 0,
        "reason": "defer_to_renewal",
    }


def test_trial_accounts_do_not_create_mid_cycle_charges() -> None:
    line = invoice_line_for_seat_change(
        account_id="acct-trial",
        old_seats=2,
        new_seats=6,
        monthly_price_cents=5000,
        change_day=3,
        billing_cycle_days=30,
        is_trial=True,
    )

    assert line == {
        "account_id": "acct-trial",
        "quantity_delta": 4,
        "amount_cents": 0,
        "reason": "trial_no_charge",
    }


def test_no_seat_change_produces_zero_amount_line() -> None:
    line = invoice_line_for_seat_change(
        account_id="acct-noop",
        old_seats=4,
        new_seats=4,
        monthly_price_cents=1200,
        change_day=12,
        billing_cycle_days=30,
    )

    assert line == {
        "account_id": "acct-noop",
        "quantity_delta": 0,
        "amount_cents": 0,
        "reason": "no_change",
    }
