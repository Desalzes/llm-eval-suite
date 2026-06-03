from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class PlanTier(str, Enum):
    STANDARD = "standard"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class RenewalState:
    account_id: str
    plan_tier: PlanTier
    invoice_due_date: date
    as_of: date
    invoice_paid: bool
    manual_hold: bool = False


@dataclass(frozen=True)
class AccessDecision:
    status: str
    access_allowed: bool
    billable: bool
    reason: str


DEFAULT_GRACE_DAYS = 7


def classify_renewal_access(state: RenewalState) -> AccessDecision:
    if state.invoice_paid:
        return AccessDecision(
            status="active",
            access_allowed=True,
            billable=True,
            reason=f"{state.account_id} invoice is paid.",
        )

    overdue_days = (state.as_of - state.invoice_due_date).days
    if overdue_days >= DEFAULT_GRACE_DAYS:
        return AccessDecision(
            status="suspended",
            access_allowed=False,
            billable=False,
            reason=f"{state.account_id} is past the renewal grace period.",
        )

    return AccessDecision(
        status="active",
        access_allowed=True,
        billable=True,
        reason=f"{state.account_id} is inside the renewal grace period.",
    )
