from __future__ import annotations

from dataclasses import dataclass


VALID_STATUSES = {"active", "paused", "closed"}


@dataclass
class Account:
    account_id: str
    email: str
    status: str


@dataclass(frozen=True)
class BatchOutcome:
    applied: list[str]
    failed: list[dict[str, str]]


class AccountStore:
    def __init__(self, accounts: list[Account]) -> None:
        self._accounts = {account.account_id: account for account in accounts}

    def get(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    def update(self, account_id: str, *, email: str | None = None, status: str | None = None) -> None:
        account = self._accounts[account_id]
        if email is not None:
            account.email = email
        if status is not None:
            account.status = status


def _valid_email(email: str) -> bool:
    local, sep, domain = email.partition("@")
    return bool(local and sep and domain)


def apply_account_updates(store: AccountStore, updates: list[dict[str, str]]) -> BatchOutcome:
    for update in updates:
        account_id = update.get("account_id", "")
        account = store.get(account_id)
        if account is None:
            return BatchOutcome(applied=[], failed=[{"account_id": account_id, "reason": "not_found"}])
        if "email" in update and not _valid_email(update["email"]):
            return BatchOutcome(applied=[], failed=[{"account_id": account_id, "reason": "invalid_email"}])
        if "status" in update and update["status"] not in VALID_STATUSES:
            return BatchOutcome(applied=[], failed=[{"account_id": account_id, "reason": "invalid_status"}])

    applied: list[str] = []
    for update in updates:
        account_id = update["account_id"]
        store.update(account_id, email=update.get("email"), status=update.get("status"))
        applied.append(account_id)

    return BatchOutcome(applied=applied, failed=[])
