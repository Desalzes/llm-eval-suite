"""One-shot bootstrap for trials/trial-1.json from the on-disk corpus.

Trial 1 = every fixture under tasks/fixtures/ EXCEPT the browser-visual ones
(no deterministic renderer in the scorer-only run.py). Category is reused from
generate_atlas_data.category_for; weight + difficulty are derived from eval-set
membership (hard/innovation -> harder + their weight). Re-run only to bootstrap;
trials/trial-1.json is hand-tunable afterward.

    python generate_trial1.py
"""
from __future__ import annotations

import json
from pathlib import Path

from generate_atlas_data import category_for

ROOT = Path(__file__).resolve().parent
EXCLUDE = {"frontend-visual-regression", "mobile-visual-contract"}  # need a browser renderer


def _membership() -> dict:
    """{fixture_id: {"weight": int, "hard": bool, "innovation": bool}} from eval-sets."""
    out = {}
    for sp in sorted((ROOT / "tasks" / "eval-sets").glob("*.json")):
        data = json.loads(sp.read_text(encoding="utf-8"))
        for t in data.get("tasks", []):
            fid = Path(t["path"]).parent.name
            rec = out.setdefault(fid, {"weight": 1, "hard": False, "innovation": False})
            rec["weight"] = max(rec["weight"], int(t.get("weight", 1)))
            if data.get("id") == "hard":
                rec["hard"] = True
            if data.get("id") == "innovation":
                rec["innovation"] = True
    return out


def build_trial1() -> dict:
    member = _membership()
    objectives = []
    for task_json in sorted((ROOT / "tasks" / "fixtures").glob("*/task.json")):
        fid = task_json.parent.name
        if fid in EXCLUDE:
            continue
        m = member.get(fid, {"weight": 2, "hard": False, "innovation": False})
        difficulty = "hard" if (m["hard"] or m["innovation"]) else "medium"
        objectives.append({
            "path": f"tasks/fixtures/{fid}/task.json",
            "weight": m["weight"] if m["weight"] > 1 else 2,
            "category": category_for(fid),
            "difficulty": difficulty,
        })
    objectives.sort(key=lambda o: (o["category"], o["path"]))
    return {
        "id": "trial-1",
        "name": "Trial 1 - The Full Bench",
        "description": ("One composite challenge spanning the eligible corpus. Run every "
                        "objective, then score once for a headline /100 plus a diagnostic "
                        "report (by category, by difficulty, failure modes, restraint)."),
        "objectives": objectives,
    }


def main() -> int:
    data = build_trial1()
    (ROOT / "trials").mkdir(exist_ok=True)
    (ROOT / "trials" / "trial-1.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote trials/trial-1.json with {len(data['objectives'])} objectives")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
