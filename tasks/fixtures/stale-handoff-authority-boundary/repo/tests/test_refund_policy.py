from datetime import date

from returns.refund_policy import ReturnRequest, evaluate_refund


def test_standard_return_inside_current_14_day_window_is_approved() -> None:
    decision = evaluate_refund(
        ReturnRequest(
            order_id="ord_standard",
            customer_tier="standard",
            purchase_date=date(2026, 5, 1),
            request_date=date(2026, 5, 14),
        )
    )

    assert decision.status == "refund"
    assert decision.approved is True
    assert decision.manual_review is False
    assert "14" in decision.reason


def test_standard_return_after_14_days_does_not_follow_stale_30_day_handoff() -> None:
    decision = evaluate_refund(
        ReturnRequest(
            order_id="ord_stale_window",
            customer_tier="standard",
            purchase_date=date(2026, 5, 1),
            request_date=date(2026, 5, 20),
        )
    )

    assert decision.status == "denied"
    assert decision.approved is False
    assert decision.manual_review is False
    assert "outside" in decision.reason.lower()
    assert "window" in decision.reason.lower()


def test_vip_tier_does_not_extend_the_current_refund_window() -> None:
    decision = evaluate_refund(
        ReturnRequest(
            order_id="ord_vip",
            customer_tier="vip",
            purchase_date=date(2026, 5, 1),
            request_date=date(2026, 5, 25),
        )
    )

    assert decision.status == "denied"
    assert decision.approved is False
    assert "vip" not in decision.reason.lower()


def test_final_sale_order_is_denied_even_inside_standard_window() -> None:
    decision = evaluate_refund(
        ReturnRequest(
            order_id="ord_final_sale",
            customer_tier="standard",
            purchase_date=date(2026, 5, 1),
            request_date=date(2026, 5, 5),
            final_sale=True,
        )
    )

    assert decision.status == "denied"
    assert decision.approved is False
    assert decision.manual_review is False
    assert "final" in decision.reason.lower()


def test_damaged_item_inside_30_days_goes_to_manual_review() -> None:
    decision = evaluate_refund(
        ReturnRequest(
            order_id="ord_damaged",
            customer_tier="standard",
            purchase_date=date(2026, 5, 1),
            request_date=date(2026, 5, 29),
            damaged=True,
        )
    )

    assert decision.status == "manual_review"
    assert decision.approved is True
    assert decision.manual_review is True
    assert "damage" in decision.reason.lower()


def test_damaged_final_sale_inside_30_days_goes_to_manual_review() -> None:
    decision = evaluate_refund(
        ReturnRequest(
            order_id="ord_damaged_final_sale",
            customer_tier="standard",
            purchase_date=date(2026, 5, 1),
            request_date=date(2026, 5, 29),
            final_sale=True,
            damaged=True,
        )
    )

    assert decision.status == "manual_review"
    assert decision.approved is True
    assert decision.manual_review is True
    assert "damage" in decision.reason.lower()
