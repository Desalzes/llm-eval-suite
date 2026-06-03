import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.eval_set_inspector import summarize_eval_set_run
from suite.eval_set_runner import run_supervised_eval_set


ROOT = Path(__file__).resolve().parents[1]


class EvalSetRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="eval-set-runner-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_profile(self, profile_id: str) -> Path:
        profile_path = self.temp_dir / f"{profile_id}.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": profile_id,
                    "name": profile_id,
                    "description": f"{profile_id} test profile.",
                    "command": [
                        sys.executable,
                        "-c",
                        (
                            "from pathlib import Path; "
                            "p=Path('calculator.py'); "
                            "text=p.read_text(encoding='utf-8'); "
                            "p.write_text(text.replace("
                            "'def subtract(left: int, right: int) -> int:\\n    return left + right', "
                            "'def subtract(left: int, right: int) -> int:\\n    return left - right'"
                            "), encoding='utf-8')"
                        ),
                    ],
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def _write_trace_profile(self, profile_id: str, tokens_used: int) -> Path:
        profile_path = self.temp_dir / f"{profile_id}.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": profile_id,
                    "name": profile_id,
                    "description": f"{profile_id} test profile.",
                    "command": [
                        sys.executable,
                        "-c",
                        (
                            "from pathlib import Path; "
                            "print('exec', flush=True); "
                            f"print('tokens used\\n{tokens_used}', flush=True); "
                            "p=Path('calculator.py'); "
                            "text=p.read_text(encoding='utf-8'); "
                            "p.write_text(text.replace("
                            "'def subtract(left: int, right: int) -> int:\\n    return left + right', "
                            "'def subtract(left: int, right: int) -> int:\\n    return left - right'"
                            "), encoding='utf-8')"
                        ),
                    ],
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def _write_timeout_profile(self, profile_id: str) -> Path:
        profile_path = self.temp_dir / f"{profile_id}.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": profile_id,
                    "name": profile_id,
                    "description": f"{profile_id} test profile.",
                    "command": [
                        sys.executable,
                        "-c",
                        "import time; print('START', flush=True); time.sleep(5)",
                    ],
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def _write_eval_set(self) -> Path:
        set_path = self.temp_dir / "core.json"
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "name": "Core Eval Set",
                    "description": "One deterministic smoke task.",
                    "tasks": [
                        {
                            "path": "tasks/examples/python-cli-bugfix/task.json",
                            "weight": 2,
                            "tags": ["smoke", "bugfix"],
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return set_path

    def test_supervised_eval_set_runs_tasks_and_writes_summary(self) -> None:
        profile_path = self._write_trace_profile("eval-set-fixer", tokens_used=10)
        set_path = self._write_eval_set()

        summary = run_supervised_eval_set(
            suite_root=ROOT,
            set_path=set_path,
            profile_path=profile_path,
            run_id="unit-eval-set",
            eval_runs_dir=self.temp_dir / "eval-runs",
            timeout_seconds=15,
            idle_timeout_seconds=15,
            max_output_bytes=4096,
            force=True,
        )

        run_dir = Path(summary["run_dir"])
        task_run_dir = run_dir / "tasks" / "01-python-cli-bugfix"

        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["status_counts"], {"passed": 1})
        self.assertEqual(summary["weighted_status_counts"], {"passed": 2})
        self.assertEqual(summary["observability"]["health"], "clean")
        self.assertEqual(summary["observability"]["runtime_hotspots"][0]["task_id"], "python-cli-bugfix")
        self.assertEqual(summary["runs"][0]["task_id"], "python-cli-bugfix")
        self.assertEqual(summary["runs"][0]["weight"], 2)
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "summary.json").exists())
        self.assertTrue((run_dir / "summary.md").exists())
        summary_md = (run_dir / "summary.md").read_text(encoding="utf-8")
        self.assertIn("## Observability", summary_md)
        self.assertIn("Health: `clean`", summary_md)
        self.assertTrue((task_run_dir / "result.json").exists())

    def test_supervised_eval_set_summarizes_trace_cost_and_runtime(self) -> None:
        summary = run_supervised_eval_set(
            suite_root=ROOT,
            set_path=self._write_eval_set(),
            profile_path=self._write_trace_profile("eval-set-trace-fixer", tokens_used=123),
            run_id="unit-eval-set-stats",
            eval_runs_dir=self.temp_dir / "eval-runs",
            timeout_seconds=15,
            idle_timeout_seconds=15,
            max_output_bytes=4096,
            force=True,
        )

        stats = summary["aggregate_stats"]
        task_stats = stats["per_task"]["python-cli-bugfix"]

        self.assertEqual(stats["run_count"], 1)
        self.assertEqual(stats["task_count"], 1)
        self.assertEqual(stats["pass_count"], 1)
        self.assertEqual(stats["unsafe_count"], 0)
        self.assertEqual(stats["timeout_count"], 0)
        self.assertEqual(stats["pass_rate"], 1.0)
        self.assertEqual(stats["unsafe_rate"], 0.0)
        self.assertEqual(stats["timeout_rate"], 0.0)
        self.assertEqual(stats["total_tokens"], 123)
        self.assertEqual(stats["runs_missing_tokens"], 0)
        self.assertEqual(stats["total_tool_calls"], 1)
        self.assertGreater(stats["total_child_runtime_seconds"], 0)
        self.assertGreater(stats["average_runtime_per_task_seconds"], 0)
        self.assertEqual(stats["cap_reason_counts"], {})
        self.assertEqual(task_stats["run_count"], 1)
        self.assertEqual(task_stats["status_counts"], {"passed": 1})
        self.assertEqual(task_stats["total_tokens"], 123)

    def test_supervised_eval_set_counts_child_timeouts_and_cap_reasons(self) -> None:
        summary = run_supervised_eval_set(
            suite_root=ROOT,
            set_path=self._write_eval_set(),
            profile_path=self._write_timeout_profile("eval-set-timeout"),
            run_id="unit-eval-set-timeout-stats",
            eval_runs_dir=self.temp_dir / "eval-runs",
            timeout_seconds=0.2,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        stats = summary["aggregate_stats"]

        self.assertEqual(summary["status"], "failed")
        self.assertEqual(stats["run_count"], 1)
        self.assertEqual(stats["timeout_count"], 1)
        self.assertEqual(stats["timeout_rate"], 1.0)
        self.assertEqual(stats["cap_reason_counts"], {"timeout_seconds": 1})

    def test_supervise_set_cli_runs_eval_set(self) -> None:
        profile_path = self._write_profile("eval-set-cli-fixer")
        set_path = self._write_eval_set()
        eval_runs_dir = self.temp_dir / "eval-runs"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "supervise-set",
                "--set",
                str(set_path),
                "--profile",
                str(profile_path),
                "--run-id",
                "cli-eval-set",
                "--eval-runs-dir",
                str(eval_runs_dir),
                "--timeout-seconds",
                "15",
                "--idle-timeout-seconds",
                "15",
                "--max-output-bytes",
                "4096",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("[supervise-set] starting cli-eval-set", completed.stderr)
        self.assertIn("[supervise-set] 01-python-cli-bugfix -> passed", completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "passed")
        self.assertTrue((eval_runs_dir / "cli-eval-set" / "summary.json").exists())

    def test_inspect_set_run_cli_can_emit_brief_operational_view(self) -> None:
        run_dir = self.temp_dir / "eval-runs" / "unit-smoke"
        run_dir.mkdir(parents=True)
        summary_path = run_dir / "summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "run_id": "unit-smoke",
                    "run_dir": str(run_dir),
                    "set_id": "smoke",
                    "set_name": "Smoke Set",
                    "set_path": str(self.temp_dir / "smoke.json"),
                    "profile_id": "codex-baseline",
                    "status": "failed",
                    "status_counts": {"passed": 1, "failed": 1},
                    "weighted_status_counts": {"passed": 1, "failed": 2},
                    "aggregate_stats": {
                        "run_count": 2,
                        "task_count": 2,
                        "pass_count": 1,
                        "pass_rate": 0.5,
                        "unsafe_rate": 0.0,
                        "timeout_rate": 0.0,
                        "total_tokens": 300,
                        "total_tool_calls": 7,
                        "total_child_runtime_seconds": 30.5,
                        "average_runtime_per_task_seconds": 15.25,
                        "cap_reason_counts": {},
                        "per_task": {
                            "fast-task": {
                                "average_runtime_per_task_seconds": 5.0,
                                "total_child_runtime_seconds": 5.0,
                                "total_tokens": 100,
                                "status_counts": {"passed": 1},
                            },
                            "slow-task": {
                                "average_runtime_per_task_seconds": 25.5,
                                "total_child_runtime_seconds": 25.5,
                                "total_tokens": 200,
                                "status_counts": {"failed": 1},
                            },
                        },
                    },
                    "observability": {
                        "health": "attention",
                        "risk_flags": ["non_passing_runs"],
                        "failure_status_counts": {"failed": 1},
                        "cap_reason_counts": {},
                        "missing_data": {"runtime": 0, "tokens": 0},
                        "recommendations": [
                            {
                                "kind": "runtime_hotspot",
                                "task_id": "slow-task",
                                "reason": "Slow task.",
                                "action": "Inspect slow-task.",
                            }
                        ],
                        "runtime_hotspots": [
                            {
                                "task_id": "slow-task",
                                "average_runtime_per_task_seconds": 25.5,
                                "total_child_runtime_seconds": 25.5,
                                "total_tokens": 200,
                            }
                        ],
                        "token_hotspots": [],
                    },
                    "runs": [
                        {
                            "task_id": "fast-task",
                            "run_id": "01-fast-task",
                            "status": "passed",
                            "weight": 1,
                            "child_status": "passed",
                            "child_cap_reason": None,
                        },
                        {
                            "task_id": "slow-task",
                            "run_id": "02-slow-task",
                            "status": "failed",
                            "weight": 2,
                            "child_status": "passed",
                            "child_cap_reason": None,
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-set-run",
                "--summary",
                str(summary_path),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["run_id"], "unit-smoke")
        self.assertEqual(brief["set_id"], "smoke")
        self.assertEqual(brief["status"], "failed")
        self.assertEqual(brief["counts"]["status"], {"failed": 1, "passed": 1})
        self.assertEqual(brief["counts"]["weighted_status"], {"failed": 2, "passed": 1})
        self.assertEqual(brief["aggregate"]["pass_rate"], 0.5)
        self.assertEqual(brief["observability"]["health"], "attention")
        self.assertEqual(brief["problem_task_ids"], ["slow-task"])
        self.assertEqual(brief["top_runtime_hotspots"][0]["task_id"], "slow-task")
        self.assertEqual(brief["next_action"], "Inspect slow-task.")
        self.assertEqual(
            brief["inspect_problem_task_commands"],
            [
                {
                    "task_id": "slow-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id slow-task --brief",
                }
            ],
        )
        self.assertEqual(
            brief["inspect_hotspot_commands"],
            [
                {
                    "task_id": "slow-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id slow-task --brief",
                }
            ],
        )
        self.assertNotIn("runs", brief)
        self.assertNotIn("aggregate_stats", brief)

    def test_inspect_set_run_brief_reports_token_and_tool_hotspots(self) -> None:
        inspected = {
            "run_id": "unit-smoke",
            "set_id": "smoke",
            "set_name": "Smoke Set",
            "profile_id": "codex-baseline",
            "status": "passed",
            "status_counts": {"passed": 3},
            "weighted_status_counts": {"passed": 5},
            "aggregate_stats": {
                "run_count": 3,
                "task_count": 3,
                "pass_count": 3,
                "pass_rate": 1.0,
                "unsafe_rate": 0.0,
                "timeout_rate": 0.0,
                "total_tokens": 10000,
                "total_tool_calls": 40,
                "total_child_runtime_seconds": 60.0,
                "average_runtime_per_task_seconds": 20.0,
                "cap_reason_counts": {},
                "per_task": {
                    "balanced-task": {
                        "average_runtime_per_task_seconds": 15.0,
                        "total_child_runtime_seconds": 15.0,
                        "total_tokens": 3000,
                        "total_tool_calls": 10,
                        "status_counts": {"passed": 1},
                    },
                    "token-heavy-task": {
                        "average_runtime_per_task_seconds": 10.0,
                        "total_child_runtime_seconds": 10.0,
                        "total_tokens": 6000,
                        "total_tool_calls": 5,
                        "status_counts": {"passed": 1},
                    },
                    "tool-heavy-task": {
                        "average_runtime_per_task_seconds": 35.0,
                        "total_child_runtime_seconds": 35.0,
                        "total_tokens": 1000,
                        "total_tool_calls": 25,
                        "status_counts": {"passed": 1},
                    },
                },
            },
            "observability": {
                "health": "clean",
                "risk_flags": [],
                "recommendations": [],
                "runtime_hotspots": [],
            },
            "runs": [],
        }

        brief = summarize_eval_set_run(inspected)

        self.assertEqual(
            brief["top_token_hotspots"],
            [
                {
                    "task_id": "token-heavy-task",
                    "average_runtime_per_task_seconds": 10.0,
                    "total_child_runtime_seconds": 10.0,
                    "total_tokens": 6000,
                    "total_tool_calls": 5,
                },
                {
                    "task_id": "balanced-task",
                    "average_runtime_per_task_seconds": 15.0,
                    "total_child_runtime_seconds": 15.0,
                    "total_tokens": 3000,
                    "total_tool_calls": 10,
                },
                {
                    "task_id": "tool-heavy-task",
                    "average_runtime_per_task_seconds": 35.0,
                    "total_child_runtime_seconds": 35.0,
                    "total_tokens": 1000,
                    "total_tool_calls": 25,
                },
            ],
        )
        self.assertEqual(
            brief["top_tool_hotspots"],
            [
                {
                    "task_id": "tool-heavy-task",
                    "average_runtime_per_task_seconds": 35.0,
                    "total_child_runtime_seconds": 35.0,
                    "total_tokens": 1000,
                    "total_tool_calls": 25,
                },
                {
                    "task_id": "balanced-task",
                    "average_runtime_per_task_seconds": 15.0,
                    "total_child_runtime_seconds": 15.0,
                    "total_tokens": 3000,
                    "total_tool_calls": 10,
                },
                {
                    "task_id": "token-heavy-task",
                    "average_runtime_per_task_seconds": 10.0,
                    "total_child_runtime_seconds": 10.0,
                    "total_tokens": 6000,
                    "total_tool_calls": 5,
                },
            ],
        )
        self.assertEqual(
            brief["inspect_token_hotspot_commands"],
            [
                {
                    "task_id": "token-heavy-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id token-heavy-task --brief",
                },
                {
                    "task_id": "balanced-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id balanced-task --brief",
                },
                {
                    "task_id": "tool-heavy-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id tool-heavy-task --brief",
                },
            ],
        )
        self.assertEqual(
            brief["inspect_tool_hotspot_commands"],
            [
                {
                    "task_id": "tool-heavy-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id tool-heavy-task --brief",
                },
                {
                    "task_id": "balanced-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id balanced-task --brief",
                },
                {
                    "task_id": "token-heavy-task",
                    "command": "python -m suite.cli inspect-run --eval-set-run-id unit-smoke --task-id token-heavy-task --brief",
                },
            ],
        )

    def test_inspect_set_run_cli_can_resolve_latest_run_for_set_id(self) -> None:
        eval_runs_dir = self.temp_dir / "eval-runs"

        for run_id, pass_rate in [("older-smoke", 0.5), ("newer-smoke", 1.0)]:
            run_dir = eval_runs_dir / run_id
            run_dir.mkdir(parents=True)
            (run_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "run_dir": str(run_dir),
                        "set_id": "smoke",
                        "set_name": "Smoke Set",
                        "profile_id": "codex-baseline",
                        "status": "passed" if pass_rate == 1.0 else "failed",
                        "status_counts": {"passed": 1},
                        "weighted_status_counts": {"passed": 2},
                        "aggregate_stats": {
                            "run_count": 1,
                            "task_count": 1,
                            "pass_count": 1 if pass_rate == 1.0 else 0,
                            "pass_rate": pass_rate,
                        },
                        "observability": {"health": "clean", "recommendations": [], "runtime_hotspots": []},
                        "runs": [],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        older_summary = eval_runs_dir / "older-smoke" / "summary.json"
        newer_summary = eval_runs_dir / "newer-smoke" / "summary.json"
        older_time = 1_700_000_000
        newer_time = 1_700_000_100
        os.utime(older_summary, (older_time, older_time))
        os.utime(newer_summary, (newer_time, newer_time))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-set-run",
                "--set-id",
                "smoke",
                "--latest",
                "--eval-runs-dir",
                str(eval_runs_dir),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["run_id"], "newer-smoke")
        self.assertEqual(brief["set_id"], "smoke")
        self.assertEqual(brief["aggregate"]["pass_rate"], 1.0)

    def test_core_eval_set_includes_low_compute_fixtures_only(self) -> None:
        data = json.loads((ROOT / "tasks/eval-sets/core.json").read_text(encoding="utf-8"))
        paths = [task["path"] for task in data["tasks"]]

        self.assertEqual(
            paths,
            [
                "tasks/examples/python-cli-bugfix/task.json",
                "tasks/fixtures/multi-file-hidden-coupling/task.json",
                "tasks/fixtures/docs-to-code-implementation/task.json",
                "tasks/fixtures/dependency-api-migration/task.json",
                "tasks/fixtures/safety-boundary-routing-config/task.json",
                "tasks/fixtures/order-dependent-state-leak/task.json",
                "tasks/fixtures/ambiguous-proration-policy/task.json",
                "tasks/fixtures/long-context-flag-precedence/task.json",
                "tasks/fixtures/skill-creator-quality/task.json",
                "tasks/fixtures/skill-progressive-disclosure/task.json",
                "tasks/fixtures/failure-classification-taxonomy/task.json",
                "tasks/fixtures/review-feedback-prioritization/task.json",
                "tasks/fixtures/untrusted-doc-instruction-boundary/task.json",
                "tasks/fixtures/temporal-cutoff-boundary/task.json",
                "tasks/fixtures/process-boundary-failure-classification/task.json",
                "tasks/fixtures/ambiguous-renewal-grace-policy/task.json",
                "tasks/fixtures/skill-metadata-scope-control/task.json",
                "tasks/fixtures/skill-script-preservation/task.json",
                "tasks/fixtures/skill-asset-bundling/task.json",
                "tasks/fixtures/skill-reference-selection/task.json",
                "tasks/fixtures/skill-scaffold-workflow/task.json",
                "tasks/fixtures/skill-prerequisite-boundary/task.json",
                "tasks/fixtures/skill-update-preservation/task.json",
                "tasks/fixtures/skill-trigger-boundary/task.json",
                "tasks/fixtures/skill-reference-instruction-boundary/task.json",
            ],
        )
        self.assertNotIn("tasks/fixtures/frontend-visual-regression/task.json", paths)

    def test_skill_script_preservation_avoids_pytest_temp_artifact_noise(self) -> None:
        repo = ROOT / "tasks/fixtures/skill-script-preservation/repo"
        pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
        test_source = (repo / "tests/test_skill_script_preservation.py").read_text(encoding="utf-8")
        gitignore = (repo / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("-p no:cacheprovider", pyproject)
        self.assertNotIn("--basetemp", pyproject)
        self.assertNotIn("tmp_path", test_source)
        self.assertIn(".pytest-tmp/", gitignore)
        self.assertIn(".pytest_cache/", gitignore)

    def test_smoke_eval_set_is_small_representative_core_subset(self) -> None:
        core = json.loads((ROOT / "tasks/eval-sets/core.json").read_text(encoding="utf-8"))
        smoke = json.loads((ROOT / "tasks/eval-sets/smoke.json").read_text(encoding="utf-8"))
        core_paths = {task["path"] for task in core["tasks"]}
        smoke_paths = [task["path"] for task in smoke["tasks"]]
        smoke_tags = {tag for task in smoke["tasks"] for tag in task["tags"]}

        self.assertEqual(smoke["id"], "smoke")
        self.assertGreaterEqual(len(smoke_paths), 4)
        self.assertLessEqual(len(smoke_paths), 6)
        self.assertTrue(set(smoke_paths).issubset(core_paths))
        self.assertNotIn("tasks/fixtures/frontend-visual-regression/task.json", smoke_paths)
        self.assertIn("smoke", smoke_tags)
        self.assertIn("multi-file", smoke_tags)
        self.assertIn("safety-boundary", smoke_tags)
        self.assertIn("skill-authoring", smoke_tags)
        self.assertIn("failure-classification", smoke_tags)
        self.assertIn("ambiguous-criteria", smoke_tags)


if __name__ == "__main__":
    unittest.main()
