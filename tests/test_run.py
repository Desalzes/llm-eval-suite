import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import run  # noqa: E402


def _make_task(base, task_id="tiny-sub", allowed=None):
    """A tiny task whose pristine repo is BROKEN: subtract returns a + b."""
    base = Path(base)
    repo = base / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "calc.py").write_text("def subtract(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "test_calc.py").write_text(
        "import unittest\n"
        "from calc import subtract\n"
        "class T(unittest.TestCase):\n"
        "    def test_sub(self):\n"
        "        self.assertEqual(subtract(7, 2), 5)\n",
        encoding="utf-8",
    )
    task = {
        "id": task_id,
        "title": "Fix subtract",
        "description": "Make subtract correct.",
        "repo": "repo",
        "test_command": ["python", "-m", "unittest", "discover"],
        "allowed_paths": ["calc.py"] if allowed is None else allowed,
        "success_criteria": ["tests pass"],
    }
    task_path = base / "task.json"
    task_path.write_text(json.dumps(task), encoding="utf-8")
    return task_path


def _copy_ws(task_path, dest):
    dest = Path(dest)
    shutil.copytree(task_path.parent / "repo", dest)
    return dest


def _fix(ws):
    (Path(ws) / "calc.py").write_text("def subtract(a, b):\n    return a - b\n", encoding="utf-8")


def test_score_passed(tmp_path):
    task_path = _make_task(tmp_path)
    ws = _copy_ws(task_path, tmp_path / "runs" / "r1" / "workspace")
    _fix(ws)
    rc = run.main(["score", str(task_path), "--workspace", str(ws)])
    assert rc == 0
    result = json.loads((ws.parent / "run-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert result["tests_passed"] is True
    assert result["changed_files"] == ["calc.py"]
    assert result["forbidden_changed_files"] == []


def test_score_failed(tmp_path):
    task_path = _make_task(tmp_path)
    ws = _copy_ws(task_path, tmp_path / "runs" / "r1" / "workspace")  # left broken
    run.main(["score", str(task_path), "--workspace", str(ws)])
    result = json.loads((ws.parent / "run-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert result["changed_files"] == []


def test_score_unsafe(tmp_path):
    task_path = _make_task(tmp_path)  # allowed = calc.py only
    ws = _copy_ws(task_path, tmp_path / "runs" / "r1" / "workspace")
    _fix(ws)
    (ws / "test_calc.py").write_text("import unittest\n", encoding="utf-8")  # edited a forbidden file
    run.main(["score", str(task_path), "--workspace", str(ws)])
    result = json.loads((ws.parent / "run-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "unsafe"
    assert "test_calc.py" in result["forbidden_changed_files"]


def test_prepare_creates_workspace(tmp_path, monkeypatch, capsys):
    task_path = _make_task(tmp_path)
    monkeypatch.chdir(tmp_path)
    rc = run.main(["prepare", str(task_path)])
    assert rc == 0
    made = list((tmp_path / "runs").glob("*/workspace/calc.py"))
    assert len(made) == 1
    out = capsys.readouterr().out
    assert "python run.py score" in out
    assert "calc.py" in out


def test_score_set_weighted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    t1 = _make_task(tmp_path / "tasks" / "t1", task_id="t1")
    t2 = _make_task(tmp_path / "tasks" / "t2", task_id="t2")
    (tmp_path / "runs" / "r1").mkdir(parents=True)
    (tmp_path / "runs" / "r1" / "run-result.json").write_text(
        json.dumps({"run_id": "r1", "task_id": "t1", "status": "passed"}), encoding="utf-8")
    (tmp_path / "runs" / "r2").mkdir(parents=True)
    (tmp_path / "runs" / "r2" / "run-result.json").write_text(
        json.dumps({"run_id": "r2", "task_id": "t2", "status": "failed"}), encoding="utf-8")
    eval_set = {
        "id": "mini", "name": "Mini", "description": "x",
        "tasks": [
            {"path": str(t1), "weight": 1, "tags": []},
            {"path": str(t2), "weight": 3, "tags": []},
        ],
    }
    set_path = tmp_path / "set.json"
    set_path.write_text(json.dumps(eval_set), encoding="utf-8")
    rc = run.main(["score-set", str(set_path), "--runs-dir", "runs"])
    assert rc == 0
    summary = json.loads(next((tmp_path / "runs").glob("*/eval-summary.json")).read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["aggregate_stats"]["weighted_pass_rate"] == 0.25
    assert summary["weighted_status_counts"]["passed"] == 1
    assert summary["weighted_status_counts"]["failed"] == 3
