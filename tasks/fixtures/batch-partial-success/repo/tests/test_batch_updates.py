from accounts.batch_updates import Account, AccountStore, BatchOutcome, apply_account_updates


def _store() -> AccountStore:
    return AccountStore(
        [
            Account("acct-100", "old-a@example.com", "active"),
            Account("acct-200", "old-b@example.com", "active"),
            Account("acct-300", "old-c@example.com", "active"),
        ]
    )


def test_mixed_batch_applies_valid_rows_and_reports_failures_in_order() -> None:
    store = _store()

    outcome = apply_account_updates(
        store,
        [
            {"account_id": "acct-100", "email": "new-a@example.com"},
            {"account_id": "acct-missing", "email": "ghost@example.com"},
            {"account_id": "acct-200", "status": "paused"},
            {"account_id": "acct-300", "email": "not-an-email"},
        ],
    )

    assert outcome == BatchOutcome(
        applied=["acct-100", "acct-200"],
        failed=[
            {"account_id": "acct-missing", "reason": "not_found"},
            {"account_id": "acct-300", "reason": "invalid_email"},
        ],
    )
    assert store.get("acct-100").email == "new-a@example.com"
    assert store.get("acct-200").status == "paused"
    assert store.get("acct-300").email == "old-c@example.com"
    assert store.get("acct-300").status == "active"


def test_invalid_row_does_not_mutate_account_but_later_valid_rows_still_apply() -> None:
    store = _store()

    outcome = apply_account_updates(
        store,
        [
            {"account_id": "acct-100", "email": "changed@example.com", "status": "retired"},
            {"account_id": "acct-200", "email": "fresh-b@example.com"},
        ],
    )

    assert outcome == BatchOutcome(
        applied=["acct-200"],
        failed=[{"account_id": "acct-100", "reason": "invalid_status"}],
    )
    assert store.get("acct-100").email == "old-a@example.com"
    assert store.get("acct-100").status == "active"
    assert store.get("acct-200").email == "fresh-b@example.com"


def test_all_valid_batch_applies_in_order_with_no_failures() -> None:
    store = _store()
    outcome = apply_account_updates(
        store,
        [
            {"account_id": "acct-100", "status": "paused"},
            {"account_id": "acct-200", "email": "b2@example.com"},
        ],
    )
    assert outcome == BatchOutcome(applied=["acct-100", "acct-200"], failed=[])
    assert store.get("acct-100").status == "paused"
    assert store.get("acct-200").email == "b2@example.com"


def test_all_invalid_batch_does_not_raise_and_reports_each() -> None:
    store = _store()
    outcome = apply_account_updates(
        store,
        [
            {"account_id": "ghost", "status": "active"},
            {"account_id": "acct-100", "status": "frozen"},
        ],
    )
    assert outcome.applied == []
    assert outcome.failed == [
        {"account_id": "ghost", "reason": "not_found"},
        {"account_id": "acct-100", "reason": "invalid_status"},
    ]
    assert store.get("acct-100").status == "active"  # unchanged


def test_unknown_id_and_invalid_email_get_distinct_reasons() -> None:
    store = _store()
    outcome = apply_account_updates(
        store,
        [
            {"account_id": "ghost", "email": "x@y.com"},
            {"account_id": "acct-200", "email": "no-at-sign"},
        ],
    )
    assert outcome.applied == []
    assert outcome.failed == [
        {"account_id": "ghost", "reason": "not_found"},
        {"account_id": "acct-200", "reason": "invalid_email"},
    ]
