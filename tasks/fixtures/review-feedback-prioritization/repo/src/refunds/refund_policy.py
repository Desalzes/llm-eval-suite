from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    order_id: str
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    discount_cents: int = 0


@dataclass(frozen=True)
class RefundPlan:
    amount_cents: int
    customer_action: str
    accounting_code: str
    note: str


def _net_order_total(order: Order) -> int:
    gross = order.subtotal_cents + order.shipping_cents + order.tax_cents
    return max(0, gross - order.discount_cents)


def calculate_refund(order: Order, reason: str) -> RefundPlan:
    if reason == "shipping_issue":
        return RefundPlan(
            amount_cents=order.shipping_cents + order.tax_cents,
            customer_action="refund_card",
            accounting_code="shipping_service_failure",
            note=f"Refund shipping and tax for {order.order_id}.",
        )

    if reason == "customer_cancelled":
        return RefundPlan(
            amount_cents=_net_order_total(order),
            customer_action="refund_card",
            accounting_code="customer_cancellation",
            note=f"Refund customer cancellation for {order.order_id}.",
        )

    if reason == "fraud_review":
        return RefundPlan(
            amount_cents=_net_order_total(order),
            customer_action="refund_card",
            accounting_code="customer_cancellation",
            note=f"Refund customer cancellation for {order.order_id}.",
        )

    return RefundPlan(
        amount_cents=0,
        customer_action="no_action",
        accounting_code="not_refundable",
        note=f"No automatic refund for {order.order_id}.",
    )
