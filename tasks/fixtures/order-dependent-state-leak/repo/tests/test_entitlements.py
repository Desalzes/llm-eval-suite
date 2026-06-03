from subscriptions.entitlements import entitlements_for


def test_plan_features_are_sorted_for_stable_snapshots() -> None:
    entitlements = entitlements_for("acct-sorted", "growth")

    assert entitlements == sorted(entitlements)
    assert entitlements == [
        "core_dashboard",
        "email_support",
        "team_seats",
        "usage_alerts",
    ]


def test_repeated_lookup_for_same_account_reflects_plan_change() -> None:
    before = entitlements_for("acct-changing-plan", "enterprise")
    after = entitlements_for("acct-changing-plan", "starter")

    assert "audit_log" in before
    assert "sso" in before
    assert after == ["core_dashboard", "email_support"]


def test_overrides_are_recomputed_for_each_lookup() -> None:
    with_override = entitlements_for(
        "acct-changing-overrides",
        "growth",
        {"add": ["priority_support"], "remove": ["usage_alerts"]},
    )
    without_override = entitlements_for("acct-changing-overrides", "growth")

    assert with_override == [
        "core_dashboard",
        "email_support",
        "priority_support",
        "team_seats",
    ]
    assert without_override == [
        "core_dashboard",
        "email_support",
        "team_seats",
        "usage_alerts",
    ]


def test_different_accounts_do_not_share_override_state() -> None:
    first = entitlements_for("acct-one", "starter", {"add": ["audit_log"]})
    second = entitlements_for("acct-two", "starter")

    assert first == ["audit_log", "core_dashboard", "email_support"]
    assert second == ["core_dashboard", "email_support"]
