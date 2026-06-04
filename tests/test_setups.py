import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import run  # noqa: E402
import generate_setups_data  # noqa: E402


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_setup(base, sid="k1", skills=("s1",), instructions="# rules\n\nbe good\n",
                mention=None):
    sdir = Path(base) / "setups" / sid
    sdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": sid,
        "name": sid.title(),
        "instructions_file": "CLAUDE.md" if instructions is not None else None,
        "skills": list(skills),
    }
    (sdir / "setup.json").write_text(json.dumps(manifest), encoding="utf-8")
    if instructions is not None:
        body = instructions + (f"\nsee {mention}\n" if mention else "")
        (sdir / "CLAUDE.md").write_text(body, encoding="utf-8")
    for sk in skills:
        _write(sdir / "skills" / sk / "SKILL.md",
               f"---\nname: {sk}\ndescription: do {sk} well.\n---\n\nbody\n")
    return sdir


def test_setup_new_scaffolds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = run.main(["setup", "new", "mykit"])
    assert rc == 0
    base = tmp_path / "setups" / "mykit"
    assert (base / "setup.json").exists()
    assert (base / "CLAUDE.md").exists()
    assert (base / "skills").is_dir()
    data = json.loads((base / "setup.json").read_text(encoding="utf-8"))
    assert data["id"] == "mykit"
    assert "setup validate mykit" in capsys.readouterr().out


def test_setup_new_refuses_existing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run.main(["setup", "new", "dup"]) == 0
    assert run.main(["setup", "new", "dup"]) == 1


def test_setup_validate_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_setup(tmp_path, "good")
    assert run.main(["setup", "validate", "good"]) == 0


def test_setup_validate_missing_skill(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sdir = _make_setup(tmp_path, "broken", skills=("present",))
    manifest = json.loads((sdir / "setup.json").read_text(encoding="utf-8"))
    manifest["skills"].append("ghost")  # no skills/ghost/SKILL.md
    (sdir / "setup.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert run.main(["setup", "validate", "broken"]) == 1


def test_setup_validate_warns_on_fixture_id(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tasks" / "fixtures" / "secret-challenge").mkdir(parents=True)
    _make_setup(tmp_path, "leaky", mention="secret-challenge")
    rc = run.main(["setup", "validate", "leaky"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "WARNING" in out and "secret-challenge" in out


def test_setup_validate_with_schema_union_types(tmp_path, monkeypatch):
    # Exercises lightweight_validate against the real schema, whose model/
    # instructions_file/context_pack use union types like ["string", "null"].
    monkeypatch.chdir(tmp_path)
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "setup.schema.json").write_text(
        (ROOT / "schemas" / "setup.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8")
    sdir = _make_setup(tmp_path, "withnull", skills=())
    manifest = json.loads((sdir / "setup.json").read_text(encoding="utf-8"))
    manifest["model"] = None
    manifest["context_pack"] = None
    (sdir / "setup.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert run.main(["setup", "validate", "withnull"]) == 0


def test_generate_setups_data_shape(tmp_path):
    _make_setup(tmp_path, "k1", skills=("verify",))
    _write(tmp_path / "leaderboard" / "entries" / "e.json",
           json.dumps({"agent_label": "x", "setup_id": "k1"}))
    data = generate_setups_data.build_setups_data(tmp_path)
    assert data["count"] == 1
    s = data["setups"][0]
    assert s["id"] == "k1"
    assert s["instructions"]["content"].startswith("# rules")
    assert s["skills"][0]["name"] == "verify"
    assert s["skills"][0]["purpose"] == "do verify well."
    assert any(f["path"] == "CLAUDE.md" for f in s["files"])
    assert s["usedInRuns"] == 1


def test_generate_setups_data_size_cap(tmp_path):
    sdir = _make_setup(tmp_path, "big", skills=())
    (sdir / "CLAUDE.md").write_text(
        "A" * (generate_setups_data.MAX_FILE_CHARS + 500), encoding="utf-8")
    data = generate_setups_data.build_setups_data(tmp_path)
    content = data["setups"][0]["instructions"]["content"]
    assert "truncated" in content
    assert len(content) <= generate_setups_data.MAX_FILE_CHARS + 50


def test_generate_setups_data_baseline_badge(tmp_path):
    sdir = Path(tmp_path) / "setups" / "floor"
    sdir.mkdir(parents=True)
    (sdir / "setup.json").write_text(
        json.dumps({"id": "floor", "name": "Floor",
                    "instructions_file": None, "skills": []}), encoding="utf-8")
    data = generate_setups_data.build_setups_data(tmp_path)
    assert data["setups"][0]["badges"] == ["baseline"]
