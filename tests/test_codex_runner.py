import json
from pathlib import Path

import codex_runner


def test_build_prompt_preserves_task_contract():
    task = {
        "id": "sample-task",
        "title": "Fix sample",
        "description": "Repair the sample behavior.",
        "allowed_paths": ["src/sample.py"],
        "test_command": ["python", "-m", "pytest"],
        "success_criteria": ["tests pass", "only allowed path changes"],
        "unsafe_changes": ["editing tests is unsafe"],
    }

    prompt = codex_runner.build_prompt(task)

    assert "Task ID: sample-task" in prompt
    assert "Allowed paths: src/sample.py" in prompt
    assert "Test command: python -m pytest" in prompt
    assert "- tests pass" in prompt
    assert "- editing tests is unsafe" in prompt


def test_build_codex_command_uses_cli_subscription_auth(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    cmd = codex_runner.build_codex_command(
        codex_executable="codex.cmd",
        model="gpt-5.4-mini",
        workspace=workspace,
        bypass_sandbox=True,
        ignore_rules=True,
        ephemeral=True,
    )

    assert cmd[:4] == ["codex.cmd", "exec", "-m", "gpt-5.4-mini"]
    assert "--dangerously-bypass-approvals-and-sandbox" in cmd
    assert "--skip-git-repo-check" in cmd
    assert "--ignore-rules" in cmd
    assert "--ephemeral" in cmd
    assert "-C" in cmd
    assert str(workspace) in cmd
    assert "OPENAI_API_KEY" not in " ".join(cmd)


def test_summarize_preserves_weighted_score(tmp_path):
    eval_set = {
        "id": "mini",
        "name": "Mini Set",
        "tasks": [
            {"path": "tasks/a/task.json", "weight": 1},
            {"path": "tasks/b/task.json", "weight": 2},
        ],
    }
    task_a = {"id": "a"}
    task_b = {"id": "b"}
    root = tmp_path
    (root / "tasks/a").mkdir(parents=True)
    (root / "tasks/b").mkdir(parents=True)
    (root / "tasks/a/task.json").write_text(json.dumps(task_a), encoding="utf-8")
    (root / "tasks/b/task.json").write_text(json.dumps(task_b), encoding="utf-8")
    eval_set_path = root / "eval.json"
    eval_set_path.write_text(json.dumps(eval_set), encoding="utf-8")

    records = [
        {"task_id": "a", "score": {"status": "passed"}, "tokens_total": 10, "wall_clock_seconds": 1.5},
        {"task_id": "b", "score": {"status": "failed"}, "tokens_total": 20, "wall_clock_seconds": 2.5},
    ]

    summary = codex_runner.summarize("gpt-test", eval_set_path, records, root)

    assert summary["status_counts"] == {"passed": 1, "failed": 1}
    assert summary["aggregate_stats"] == {
        "weighted_pass_rate": 0.3333,
        "passed_weight": 1,
        "total_weight": 3,
    }
    assert summary["tokens_total"] == 30
    assert summary["wall_clock_seconds"] == 4.0
