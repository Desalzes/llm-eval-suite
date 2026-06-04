"""Hidden grader: roman(n) must match a reference for the full 1..3999 range.

Runs OUTSIDE the agent's workspace (never copied by `prepare`). The scorer runs
this after the visible tests, with EVAL_WORKSPACE pointing at the solved workspace.
A solution that only hard-codes the visible examples passes the visible tests but
fails here.
"""
import os
import sys

sys.path.insert(0, os.environ["EVAL_WORKSPACE"])
from roman import roman  # noqa: E402

_TABLE = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def reference(n):
    out = []
    for value, sym in _TABLE:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def main():
    mismatches = []
    for n in range(1, 4000):
        if roman(n) != reference(n):
            mismatches.append((n, roman(n), reference(n)))
            if len(mismatches) >= 5:
                break
    if mismatches:
        print("GRADER FAIL: roman() disagrees with the reference at:")
        for n, got, want in mismatches:
            print(f"  {n}: got {got!r}, want {want!r}")
        return 1
    print("GRADER OK: roman(n) matches the reference for 1..3999")
    return 0


if __name__ == "__main__":
    sys.exit(main())
