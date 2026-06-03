"""Generate ``atlas-data.js`` from the real testing-suite corpus.

The visual atlas (``index.html`` + ``app.js``) renders from ``window.ATLAS_DATA``.
This script derives that blob from the on-disk corpus — every ``tasks/fixtures/*/task.json``,
the eval-sets, schemas, profiles, standards, context packs, and the test files —
so the atlas always reflects reality instead of a hand-maintained copy.

Run::

    python generate_atlas_data.py

Output is deterministic: it depends only on the on-disk corpus and is sorted, so
re-running without corpus changes produces byte-identical output.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Canonical category list + colors, carried over from the first hand-built atlas
# so the visual identity is stable. "Research" has no fixture today but is kept
# as a reserved lane.
CATEGORIES = ["All", "Bugfix", "Policy", "Safety", "Skill", "Research", "Frontend", "Innovation"]

PALETTE = {
    "Bugfix": "#4477aa",
    "Policy": "#d79728",
    "Safety": "#d95b45",
    "Skill": "#167c72",
    "Research": "#7a629c",
    "Frontend": "#5e8f46",
    "Innovation": "#202426",
}

# Editorial category assignments (ported from the first hand-built atlas). Some
# fixtures sit in a category that pure id-keyword inference would miss
# (e.g. docs-to-code -> Policy, skill-reference-instruction-boundary -> Safety),
# so the explicit map is the source of truth; _infer_category only covers
# fixtures added later that are not listed here.
CATEGORY_BY_ID = {
    "ambiguous-proration-policy": "Policy",
    "ambiguous-renewal-grace-policy": "Policy",
    "dependency-api-migration": "Bugfix",
    "docs-to-code-implementation": "Policy",
    "failure-classification-taxonomy": "Bugfix",
    "frontend-visual-regression": "Frontend",
    "innovation-construction-counterexample": "Innovation",
    "innovation-mixed-representation-search": "Innovation",
    "long-context-flag-precedence": "Policy",
    "multi-file-hidden-coupling": "Bugfix",
    "order-dependent-state-leak": "Bugfix",
    "process-boundary-failure-classification": "Bugfix",
    "review-feedback-prioritization": "Policy",
    "safety-boundary-routing-config": "Safety",
    "skill-asset-bundling": "Skill",
    "skill-creator-quality": "Skill",
    "skill-metadata-scope-control": "Skill",
    "skill-prerequisite-boundary": "Skill",
    "skill-progressive-disclosure": "Skill",
    "skill-reference-instruction-boundary": "Safety",
    "skill-reference-selection": "Skill",
    "skill-scaffold-workflow": "Skill",
    "skill-script-preservation": "Skill",
    "skill-trigger-boundary": "Skill",
    "skill-update-preservation": "Skill",
    "stale-handoff-authority-boundary": "Safety",
    "temporal-cutoff-boundary": "Policy",
    "untrusted-doc-instruction-boundary": "Safety",
}


def _infer_category(task_id: str) -> str:
    tid = task_id.lower()
    if "innovation" in tid:
        return "Innovation"
    if "frontend" in tid or "visual" in tid:
        return "Frontend"
    if any(k in tid for k in ("safety", "untrusted", "authority", "instruction-boundary")):
        return "Safety"
    if "skill" in tid:
        return "Skill"
    if any(k in tid for k in ("policy", "ambiguous", "proration", "renewal", "temporal",
                              "docs-to-code", "flag", "review")):
        return "Policy"
    return "Bugfix"


def category_for(task_id: str) -> str:
    return CATEGORY_BY_ID.get(task_id, _infer_category(task_id))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_files(directory: Path, pattern: str = "*") -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.glob(pattern) if p.is_file())


def _fixture_record(task: dict) -> dict:
    task_id = task["id"]
    return {
        "id": task_id,
        "category": category_for(task_id),
        "title": task.get("title", task_id),
        "command": " ".join(task.get("test_command", [])),
        "allowed": ", ".join(task.get("allowed_paths", [])),
        "criteria": len(task.get("success_criteria", [])),
        "unsafe": len(task.get("unsafe_changes", [])),
        "summary": task.get("description", ""),
    }


def _collect_fixtures(root: Path) -> list[dict]:
    fixtures_dir = root / "tasks" / "fixtures"
    records = [_fixture_record(_load_json(p)) for p in sorted(fixtures_dir.glob("*/task.json"))]
    records.sort(key=lambda r: r["id"])
    return records


def _collect_eval_sets(root: Path) -> list[dict]:
    eval_dir = root / "tasks" / "eval-sets"
    sets = []
    for path in sorted(eval_dir.glob("*.json")):
        data = _load_json(path)
        tasks = data.get("tasks", [])
        sets.append({
            "id": data.get("id", path.stem),
            "name": data.get("name", path.stem.replace("-", " ").title()),
            "tasks": len(tasks),
            "weight": sum(int(t.get("weight", 1)) for t in tasks),
        })
    sets.sort(key=lambda s: s["id"])
    return sets


def build_atlas_data(root: Path = ROOT) -> dict:
    root = Path(root)
    fixtures = _collect_fixtures(root)
    eval_sets = _collect_eval_sets(root)
    return {
        "summary": {
            "fixtureCount": len(fixtures),
            "testFileCount": _count_files(root / "tests", "*.py"),
            "evalSetCount": len(eval_sets),
            "schemaCount": _count_files(root / "schemas", "*.json"),
            "profileCount": _count_files(root / "profiles", "*.json"),
            "standardsCount": _count_files(root / "standards"),
            "contextPackCount": _count_files(root / "context-packs"),
        },
        "categories": list(CATEGORIES),
        "palette": dict(PALETTE),
        "evalSets": eval_sets,
        "fixtures": fixtures,
    }


def write_atlas_data_js(root: Path, out_path: Path) -> dict:
    data = build_atlas_data(root)
    blob = json.dumps(data, indent=2)
    text = (
        "// AUTO-GENERATED by generate_atlas_data.py - do not edit by hand.\n"
        "// Regenerate: python generate_atlas_data.py\n"
        f"window.ATLAS_DATA = {blob};\n"
    )
    Path(out_path).write_text(text, encoding="utf-8")
    return data


def main() -> int:
    out = ROOT / "atlas-data.js"
    data = write_atlas_data_js(ROOT, out)
    s = data["summary"]
    print(
        f"Wrote {out}\n"
        f"  fixtures={s['fixtureCount']} evalSets={s['evalSetCount']} "
        f"schemas={s['schemaCount']} tests={s['testFileCount']} "
        f"profiles={s['profileCount']} standards={s['standardsCount']} "
        f"contextPacks={s['contextPackCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
