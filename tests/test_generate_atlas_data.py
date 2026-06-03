"""Tests for the atlas-data generator.

These assert the generated atlas data is derived from — and stays consistent
with — the real on-disk corpus (task.json files, eval-sets, schemas, tests),
so the visual atlas can never silently drift from the suite.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import generate_atlas_data as gen


def _fixture_dirs():
    return sorted(p for p in (ROOT / "tasks" / "fixtures").glob("*") if (p / "task.json").exists())


def test_summary_counts_match_real_corpus():
    data = gen.build_atlas_data(ROOT)
    s = data["summary"]
    assert s["fixtureCount"] == len(_fixture_dirs())
    assert len(data["fixtures"]) == s["fixtureCount"]
    assert s["schemaCount"] == len(list((ROOT / "schemas").glob("*.json")))
    assert s["evalSetCount"] == len(list((ROOT / "tasks" / "eval-sets").glob("*.json")))
    assert len(data["evalSets"]) == s["evalSetCount"]
    assert s["testFileCount"] == len(list((ROOT / "tests").glob("*.py")))


def test_every_fixture_has_required_fields():
    data = gen.build_atlas_data(ROOT)
    valid_categories = set(data["categories"])
    ids = [f["id"] for f in data["fixtures"]]
    assert len(ids) == len(set(ids)), "fixture ids must be unique"
    for f in data["fixtures"]:
        for key in ["id", "category", "title", "command", "allowed", "criteria", "unsafe", "summary"]:
            assert key in f, f"{f.get('id')} missing {key}"
        assert f["id"] and f["title"] and f["command"] and f["summary"]
        assert f["category"] in valid_categories
        assert isinstance(f["criteria"], int) and f["criteria"] >= 1
        assert isinstance(f["unsafe"], int) and f["unsafe"] >= 0
        # command is derived from the real test_command array
        assert ("python" in f["command"]) or ("npm" in f["command"])
        # title/summary are the real task metadata, not a hand-typed editorial copy
        task = json.loads((ROOT / "tasks" / "fixtures" / f["id"] / "task.json").read_text(encoding="utf-8"))
        assert f["title"] == task["title"]
        assert f["summary"] == task["description"]


def test_innovation_fixtures_present_and_categorized():
    data = gen.build_atlas_data(ROOT)
    by_id = {f["id"]: f for f in data["fixtures"]}
    for fid in ["innovation-mixed-representation-search", "innovation-construction-counterexample"]:
        assert fid in by_id, f"missing {fid}"
        assert by_id[fid]["category"] == "Innovation"
    assert "Innovation" in data["categories"]


def test_eval_sets_have_counts_and_weights():
    data = gen.build_atlas_data(ROOT)
    assert data["evalSets"], "expected at least one eval set"
    for s in data["evalSets"]:
        for key in ["id", "name", "tasks", "weight"]:
            assert key in s, f"eval set missing {key}: {s}"
        assert isinstance(s["tasks"], int) and s["tasks"] >= 0
        assert isinstance(s["weight"], (int, float))


def test_reference_counts_present():
    s = gen.build_atlas_data(ROOT)["summary"]
    for key in ["profileCount", "standardsCount", "contextPackCount"]:
        assert key in s and isinstance(s[key], int) and s[key] >= 0


def test_emitted_atlas_data_js_is_loadable(tmp_path):
    out = tmp_path / "atlas-data.js"
    gen.write_atlas_data_js(ROOT, out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("// AUTO-GENERATED")
    marker = "window.ATLAS_DATA = "
    assert marker in text
    json_blob = text.split(marker, 1)[1].rsplit(";", 1)[0].strip()
    parsed = json.loads(json_blob)
    assert parsed["summary"]["fixtureCount"] == len(_fixture_dirs())
    assert parsed["fixtures"] and parsed["evalSets"]
