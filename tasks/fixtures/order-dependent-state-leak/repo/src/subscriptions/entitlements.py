from __future__ import annotations

PLAN_FEATURES = {
    "starter": {"core_dashboard", "email_support"},
    "growth": {"core_dashboard", "email_support", "team_seats", "usage_alerts"},
    "enterprise": {
        "core_dashboard",
        "email_support",
        "team_seats",
        "usage_alerts",
        "audit_log",
        "sso",
    },
}

_ENTITLEMENT_CACHE: dict[str, list[str]] = {}


def entitlements_for(
    account_id: str,
    plan: str,
    overrides: dict[str, list[str]] | None = None,
) -> list[str]:
    if account_id in _ENTITLEMENT_CACHE:
        return _ENTITLEMENT_CACHE[account_id]

    features = set(PLAN_FEATURES[plan])
    if overrides:
        features.update(overrides.get("add", []))
        features.difference_update(overrides.get("remove", []))

    entitlements = sorted(features)
    _ENTITLEMENT_CACHE[account_id] = entitlements
    return entitlements
