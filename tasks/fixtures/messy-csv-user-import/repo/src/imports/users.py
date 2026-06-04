from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportIssue:
    line: int
    email: str | None
    reason: str


@dataclass(frozen=True)
class ImportResult:
    users: list[dict[str, str]]
    issues: list[ImportIssue]


def import_users(csv_text: str) -> ImportResult:
    lines = csv_text.strip().splitlines()
    users: list[dict[str, str]] = []

    for raw_line in lines[1:]:
        name, email, role = raw_line.split(",")
        users.append(
            {
                "name": name,
                "email": email,
                "role": role or "member",
            }
        )

    return ImportResult(users=users, issues=[])
