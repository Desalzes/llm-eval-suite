from flags.resolver import resolve_flag


def test_user_override_wins_over_environment_true() -> None:
    result = resolve_flag("search_v2", user_id="user-123", cohort="beta")

    assert result == {
        "flag": "search_v2",
        "enabled": False,
        "source": "user",
    }


def test_user_false_wins_over_cohort_true() -> None:
    result = resolve_flag("beta_dashboard", user_id="user-disabled", cohort="beta")

    assert result == {
        "flag": "beta_dashboard",
        "enabled": False,
        "source": "user",
    }


def test_cohort_override_wins_over_environment_and_default() -> None:
    result = resolve_flag("audit_export", cohort="beta")

    assert result == {
        "flag": "audit_export",
        "enabled": True,
        "source": "cohort",
    }


def test_environment_override_wins_over_default() -> None:
    result = resolve_flag("search_v2")

    assert result == {
        "flag": "search_v2",
        "enabled": True,
        "source": "environment",
    }


def test_default_is_used_when_no_higher_precedence_value_exists() -> None:
    result = resolve_flag("beta_dashboard")

    assert result == {
        "flag": "beta_dashboard",
        "enabled": False,
        "source": "default",
    }


def test_unknown_flag_uses_implicit_default() -> None:
    result = resolve_flag("does_not_exist", user_id="user-123", cohort="beta")

    assert result == {
        "flag": "does_not_exist",
        "enabled": False,
        "source": "implicit_default",
    }
