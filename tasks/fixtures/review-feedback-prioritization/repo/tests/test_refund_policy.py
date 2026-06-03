from refunds.refund_policy import Order, calculate_refund


def sample_order() -> Order:
    return Order(
        order_id="ord_123",
        subtotal_cents=10_000,
        shipping_cents=900,
        tax_cents=720,
        discount_cents=1_000,
    )


def test_fraud_review_orders_are_held_for_manual_review_without_refund() -> None:
    plan = calculate_refund(sample_order(), "fraud_review")

    assert plan.amount_cents == 0
    assert plan.customer_action == "manual_review"
    assert plan.accounting_code == "fraud_hold"
    assert "ord_123" in plan.note
    assert "fraud review" in plan.note.lower()


def test_customer_cancellation_still_refunds_net_order_total() -> None:
    plan = calculate_refund(sample_order(), "customer_cancelled")

    assert plan.amount_cents == 10_620
    assert plan.customer_action == "refund_card"
    assert plan.accounting_code == "customer_cancellation"


def test_refund_amount_never_goes_negative_when_discount_exceeds_total() -> None:
    order = Order(
        order_id="ord_discount",
        subtotal_cents=500,
        shipping_cents=0,
        tax_cents=0,
        discount_cents=1_000,
    )

    plan = calculate_refund(order, "customer_cancelled")

    assert plan.amount_cents == 0
    assert plan.customer_action == "refund_card"
    assert plan.accounting_code == "customer_cancellation"


def test_shipping_issue_still_refunds_only_shipping_and_tax() -> None:
    plan = calculate_refund(sample_order(), "shipping_issue")

    assert plan.amount_cents == 1_620
    assert plan.customer_action == "refund_card"
    assert plan.accounting_code == "shipping_service_failure"


def test_unknown_reasons_stay_non_refundable() -> None:
    plan = calculate_refund(sample_order(), "buyer_remorse_after_window")

    assert plan.amount_cents == 0
    assert plan.customer_action == "no_action"
    assert plan.accounting_code == "not_refundable"
