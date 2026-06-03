from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ReturnRequest:
    order_id: str
    customer_tier: str
    purchase_date: date
    request_date: date
    final_sale: bool = False
    damaged: bool = False


@dataclass(frozen=True)
class RefundDecision:
    status: str
    approved: bool
    manual_review: bool
    reason: str


def evaluate_refund(request: ReturnRequest) -> RefundDecision:
    days_since_purchase = (request.request_date - request.purchase_date).days
    window_days = 45 if request.customer_tier == "vip" else 30

    if days_since_purchase <= window_days:
        return RefundDecision(
            status="refund",
            approved=True,
            manual_review=False,
            reason=f"{request.order_id} is inside the legacy refund window.",
        )

    return RefundDecision(
        status="denied",
        approved=False,
        manual_review=False,
        reason=f"{request.order_id} is outside the legacy refund window.",
    )
