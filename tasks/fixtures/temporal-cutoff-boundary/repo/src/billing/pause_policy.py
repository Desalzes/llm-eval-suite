from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


CUTOFF_HOUR = 17


@dataclass(frozen=True)
class PauseRequest:
    account_id: str
    requested_at: datetime
    account_timezone: str


@dataclass(frozen=True)
class PauseDecision:
    effective_date: date
    reason: str


def _next_day(value: date) -> date:
    return value + timedelta(days=1)


def calculate_pause_effective_date(request: PauseRequest) -> PauseDecision:
    requested_at = request.requested_at
    effective = requested_at.date()

    if requested_at.hour > CUTOFF_HOUR:
        effective = _next_day(effective)
        reason = f"Pause for {request.account_id} requested after cutoff."
    else:
        reason = f"Pause for {request.account_id} requested before cutoff."

    return PauseDecision(effective_date=effective, reason=reason)
