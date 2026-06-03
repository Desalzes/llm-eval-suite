from __future__ import annotations


def invoice_line_for_seat_change(
    account_id: str,
    old_seats: int,
    new_seats: int,
    monthly_price_cents: int,
    change_day: int,
    billing_cycle_days: int,
    is_trial: bool = False,
) -> dict:
    quantity_delta = new_seats - old_seats
    amount_cents = quantity_delta * monthly_price_cents
    return {
        "account_id": account_id,
        "quantity_delta": quantity_delta,
        "amount_cents": amount_cents,
        "reason": "seat_change",
    }
