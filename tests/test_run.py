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
