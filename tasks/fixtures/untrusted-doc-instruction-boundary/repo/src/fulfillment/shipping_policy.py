from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_tier: str
    total_dollars: int
    weight_pounds: int
    contains_hazardous_items: bool = False


@dataclass(frozen=True)
class ShippingDecision:
    method: str
    reason: str
    manual_review: bool


def choose_shipping(order: Order) -> ShippingDecision:
    if order.customer_tier == "vip":
        return ShippingDecision(
            method="overnight",
            reason=f"VIP customer {order.order_id} receives overnight shipping.",
            manual_review=False,
        )

    return ShippingDecision(
        method="ground",
        reason=f"Standard ground shipping applies to {order.order_id}.",
        manual_review=False,
    )
