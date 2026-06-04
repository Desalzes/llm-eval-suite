"""Hidden grader for batch-partial-success.

Runs OUTSIDE the agent's workspace. Compares the agent's apply_account_updates
against a contract-faithful reference on a hidden batch, so a solution that
hard-codes the visible cases fails here. Only behaviours pinned by
docs/batch-update-contract.md are checked (clearly-valid / clearly-invalid only).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.environ["EVAL_WORKSPACE"], "src"))
from accounts.batch_updates import Account, AccountStore, apply_account_updates  # noqa: E402

VALID_STATUSES = {"active", "paused", "closed"}


def _valid_email(email):
    local, sep, domain = email.partition("@")
    return email.count("@") == 1 and bool(local) and bool(domain)


# (id, email, status) seed accounts
SEED = [
    ("a-1", "a1@old.com", "active"),
    ("a-2", "a2@old.com", "active"),
    ("a-3", "a3@old.com", "paused"),
]

# Hidden batch: different ids/values than the visible test.
UPDATES = [
    {"account_id": "a-1", "email": "a1@new.com"},        # ok
    {"account_id": "ghost", "status": "active"},          # not_found
    {"account_id": "a-2", "status": "closed"},            # ok
    {"account_id": "a-3", "email": "no-at-sign"},         # invalid_email
    {"account_id": "a-1", "status": "frozen"},            # invalid_status
    {"account_id": "a-2", "email": "a2@new.com", "status": "paused"},  # ok (both fields)
]


def _reference():
    store = {i: {"email": e, "status": s} for i, e, s in SEED}
    applied, failed = [], []
    for u in UPDATES:
        aid = u.get("account_id", "")
        if aid not in store:
            failed.append({"account_id": aid, "reason": "not_found"})
            continue
        if "email" in u and not _valid_email(u["email"]):
            failed.append({"account_id": aid, "reason": "invalid_email"})
            continue
        if "status" in u and u["status"] not in VALID_STATUSES:
            failed.append({"account_id": aid, "reason": "invalid_status"})
            continue
        if "email" in u:
            store[aid]["email"] = u["email"]
        if "status" in u:
            store[aid]["status"] = u["status"]
        applied.append(aid)
    return applied, failed, store


def main():
    store = AccountStore([Account(i, e, s) for i, e, s in SEED])
    outcome = apply_account_updates(store, [dict(u) for u in UPDATES])
    ref_applied, ref_failed, ref_store = _reference()

    if list(outcome.applied) != ref_applied:
        print(f"GRADER FAIL: applied mismatch\n  got:  {list(outcome.applied)}\n  want: {ref_applied}")
        return 1
    if list(outcome.failed) != ref_failed:
        print(f"GRADER FAIL: failed mismatch\n  got:  {list(outcome.failed)}\n  want: {ref_failed}")
        return 1
    for aid, ref in ref_store.items():
        acct = store.get(aid)
        if acct.email != ref["email"] or acct.status != ref["status"]:
            print(f"GRADER FAIL: account {aid} state mismatch\n"
                  f"  got:  email={acct.email} status={acct.status}\n"
                  f"  want: email={ref['email']} status={ref['status']}")
            return 1
    print("GRADER OK: apply_account_updates matches the contract on a hidden batch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
