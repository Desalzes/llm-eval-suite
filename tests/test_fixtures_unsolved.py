"""Guardrail: every fixture must ship UNSOLVED.

For each task whose test_command is python-based and runnable here, copy the
pristine repo/ and assert its own tests FAIL on the unmodified code -- proving the
challenge is real and no solution leaked. Non-python or unavailable-command
fixtures (e.g. the Node/Playwright frontend task) are skipped (manual check).
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _task_files():
    out = []
    for base in (ROOT / "tasks" / "fixtures", ROOT / "tasks" / "examples"):
        if base.exists():
            out += sorted(base.glob("*/task.json"))
    return out


@pytest.mark.parametrize("task_path", _task_files(), ids=lambda p: p.parent.name)
def test_fixture_ships_unsolved(task_path):
    task = json.loads(task_path.read_text(encoding="utf-8"))
    cmd = task["test_command"]
    if not cmd or cmd[0] != "python":
        pytest.skip(f"non-python test_command ({cmd[:1]}) - manual check")
    repo = task_path.parent / task["repo"]
    if not repo.is_dir():
        pytest.skip("no repo/ dir")
    tmp = Path(tempfile.mkdtemp(prefix="unsolved-"))
    try:
        ws = tmp / "ws"
        shutil.copytree(repo, ws, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"))
        try:
            proc = subprocess.run(cmd, cwd=str(ws), capture_output=True, text=True, timeout=300)
        except FileNotFoundError:
            pytest.skip(f"command not available: {cmd[0]}")
        assert proc.returncode != 0, (
            f"{task_path.parent.name}: unmodified fixture PASSES its tests - "
            "it ships solved (no real challenge)."
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
