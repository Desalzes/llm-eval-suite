"""Hidden grader for messy-csv-user-import.

Runs OUTSIDE the agent's workspace (never copied by `prepare`). Compares the
agent's import_users against a contract-faithful reference on inputs the agent
never saw, so a solution that hard-codes the visible test rows fails here.
Only behaviours that docs/import-contract.md pins unambiguously are checked.
"""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.join(os.environ["EVAL_WORKSPACE"], "src"))
from imports.users import import_users  # noqa: E402


def _reference(csv_text):
    users, issues, seen = [], [], set()
    for i, row in enumerate(csv.reader(io.StringIO(csv_text)), start=1):
        if i == 1:
            continue  # header
        cells = [c.strip() for c in row]
        if len(cells) != 3:
            issues.append((i, None, "malformed_row"))
            continue
        name, email, role = cells
        email = email.lower()
        if not email:
            issues.append((i, None, "missing_email"))
            continue
        if email in seen:
            issues.append((i, email, "duplicate_email"))
            continue
        seen.add(email)
        users.append({"name": name, "email": email, "role": role or "member"})
    return users, issues


# Hidden cases: same contract behaviours as the visible test, but DIFFERENT data
# (so a solve that hard-codes the visible rows fails). Only contract-clear rows.
CASES = [
    "\n".join([
        "name,email,role",
        '"Ortiz, Ana",ANA@Mail.COM,Lead',   # quoted comma + lowercase + role
        "  Wu Lei ,  WU@mail.com ,  ",       # trim + blank role -> member
        "Missing Email,,viewer",             # missing_email (line 4)
        "Dup Ana,ana@mail.com,owner",        # duplicate of line 2 (line 5)
        "JustOneField",                      # malformed_row (line 6)
        "Kim Park,kim@mail.com,ops",         # valid (line 7)
    ]),
    "name,email,role\nSolo Dev,SOLO@dev.io,\n",  # single valid row, blank role
]


def _norm_issues(issues):
    out = []
    for it in issues:
        out.append((getattr(it, "line", None), getattr(it, "email", None), getattr(it, "reason", None)))
    return out


def main():
    for idx, text in enumerate(CASES):
        result = import_users(text)
        got_users = list(result.users)
        got_issues = _norm_issues(result.issues)
        ref_users, ref_issues = _reference(text)
        if got_users != ref_users:
            print(f"GRADER FAIL: case {idx} users mismatch")
            print(f"  got:  {got_users}")
            print(f"  want: {ref_users}")
            return 1
        if got_issues != ref_issues:
            print(f"GRADER FAIL: case {idx} issues mismatch")
            print(f"  got:  {got_issues}")
            print(f"  want: {ref_issues}")
            return 1
    print("GRADER OK: import_users matches the contract on hidden cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
