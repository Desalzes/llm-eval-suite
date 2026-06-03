import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.loop_status_report import build_loop_status_report, render_loop_status_report


ROOT = Path(__file__).resolve().parents[1]


class LoopStatusReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="loop-status-report-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_task(self, task_id: str) -> Path:
        task_path = self.temp_dir / f"{task_id}.json"
        task_path.write_text(
            json.dumps(
                {
                    "id": task_id,
                    "title": task_id,
                    "description": task_id,
                    "repo": ".",
                    "test_command": ["python", "-m", "pytest"],
                    "allowed_paths": [],
                    "success_criteria": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return task_path

    def _write_summary(self) -> Path:
        slow_task = self._write_task("slow-task")
        fast_task = self._write_task("fast-task")
        new_task = self._write_task("new-task")
        set_path = self.temp_dir / "core.json"
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "tasks": [
                        {"path": str(slow_task), "weight": 2},
                        {"path": str(fast_task), "weight": 1},
                        {"path": str(new_task), "weight": 2},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        loop_dir = self.temp_dir / "improvement-runs" / "unit-loop"
        loop_dir.mkdir(parents=True)
        summary_path = loop_dir / "summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "loop_id": "unit-loop",
                    "loop_dir": str(loop_dir),
                    "profile_id": "codex-baseline",
                    "set_path": str(set_path),
                    "iterations_completed": 1,
                    "decision_counts": {"keep": 1},
                    "next_action": {
                        "kind": "expand_eval_set",
                        "reason": "All measured tasks passed.",
                    },
                    "aggregate_stats": {
                        "run_count": 2,
                        "task_count": 2,
                        "pass_count": 2,
                        "pass_rate": 1.0,
                        "unsafe_rate": 0.0,
                        "timeout_rate": 0.0,
                        "total_tokens": 90000,
                        "total_tool_calls": 90,
                        "total_child_runtime_seconds": 1800.0,
                        "average_runtime_per_task_seconds": 900.0,
                        "cap_reason_counts": {},
                        "per_task": {
                            "slow-task": {
                                "run_count": 1,
                                "pass_rate": 1.0,
                                "unsafe_rate": 0.0,
                                "timeout_rate": 0.0,
                                "total_tokens": 70000,
                                "total_tool_calls": 70,
                                "total_child_runtime_seconds": 1200.0,
                                "average_runtime_per_task_seconds": 1200.0,
                                "status_counts": {"passed": 1},
                                "cap_reason_counts": {},
                            },
                            "fast-task": {
                                "run_count": 1,
                                "pass_rate": 1.0,
                                "unsafe_rate": 0.0,
                                "timeout_rate": 0.0,
                                "total_tokens": 20000,
                                "total_tool_calls": 20,
                                "total_child_runtime_seconds": 600.0,
                                "average_runtime_per_task_seconds": 600.0,
                                "status_counts": {"passed": 1},
                                "cap_reason_counts": {},
                            },
                        },
                    },
                    "observability": {
                        "health": "clean",
                        "risk_flags": [],
                        "failure_status_counts": {},
                        "cap_reason_counts": {},
                        "missing_data": {"tokens": 0, "runtime": 0},
                        "runtime_hotspots": [],
                        "token_hotspots": [],
                        "tool_call_hotspots": [],
                        "recommendations": [
                            {
                                "kind": "runtime_hotspot",
                                "task_id": "slow-task",
                                "action": "Inspect the slow task first.",
                            }
                        ],
                    },
                    "iterations": [
                        {
                            "iteration": 1,
                            "cycle_id": "unit-loop-01",
                            "decision_status": "keep",
                            "baseline_status": "passed",
                            "decision_reason": "All measured tasks passed.",
                            "status_counts": {"passed": 2},
                            "weighted_status_counts": {"passed": 3},
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        validation_dir = self.temp_dir / "supervised-runs" / "new-task-validation-01"
        validation_dir.mkdir(parents=True)
        (validation_dir / "manifest.json").write_text(
            json.dumps({"run_id": "new-task-validation-01", "task_id": "new-task"}) + "\n",
            encoding="utf-8",
        )
        (validation_dir / "result.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "tests_passed": True,
                    "child_status": "passed",
                    "test_exit_code": 0,
                    "child_duration_seconds": 300.0,
                    "child_trace": {
                        "tokens_used": 6000,
                        "tool_call_count": 12,
                    },
                    "forbidden_changed_files": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return summary_path

    def test_report_dict_summarizes_baseline_and_throughput(self) -> None:
        summary_path = self._write_summary()

        report = build_loop_status_report(
            summary_path,
            validation_runs_dir=self.temp_dir / "supervised-runs",
            heartbeat_interval_minutes=20,
        )

        self.assertEqual(report["loop_id"], "unit-loop")
        self.assertEqual(report["baseline"]["result"], "2/2 passed")
        self.assertEqual(report["baseline"]["set_drift"], "stale")
        self.assertEqual(report["baseline"]["separate_validation_status"], "covered")
        self.assertEqual(report["baseline"]["safety"], "clean")
        self.assertEqual(report["hotspots"]["runtime"][0]["task_id"], "slow-task")
        self.assertEqual(report["throughput"]["heartbeat_interval_minutes"], 20.0)
        self.assertEqual(report["throughput"]["latest_full_loop_runtime_minutes"], 30.0)
        self.assertEqual(report["throughput"]["average_child_task_runtime_minutes"], 15.0)
        self.assertEqual(report["throughput"]["latest_validation_runtime_minutes"], 5.0)
        self.assertEqual(report["throughput"]["token_burn_per_minute"], 3000.0)
        self.assertEqual(report["throughput"]["tool_call_burn_per_minute"], 3.0)
        self.assertEqual(report["throughput"]["idle_risk"], "unknown")
        self.assertEqual(report["throughput"]["overlap_risk"], "high")
        self.assertEqual(report["throughput"]["utilization"], "aggressive")
        self.assertIn("do not run full loops every 20.0 minutes", report["recommended_next_action"])

    def test_report_renders_concise_markdown(self) -> None:
        summary_path = self._write_summary()
        report = build_loop_status_report(
            summary_path,
            validation_runs_dir=self.temp_dir / "supervised-runs",
            heartbeat_interval_minutes=20,
        )

        markdown = render_loop_status_report(report)

        self.assertIn("# Loop Status Report\n", markdown)
        self.assertIn("## Baseline\n", markdown)
        self.assertIn("- Result: 2/2 passed, weight 3.", markdown)
        self.assertIn("- Set drift: stale; separate validation covered; unmeasured `new-task`.", markdown)
        self.assertIn("## Throughput\n", markdown)
        self.assertIn("- Heartbeat interval: 20.0 min.", markdown)
        self.assertIn("- Latest measured full-loop runtime: 30.0 min.", markdown)
        self.assertIn("- Utilization: aggressive; overlap risk high; idle risk unknown.", markdown)
        self.assertIn("## Recommended Next Action\n", markdown)

    def test_cli_prints_markdown_report_for_latest_loop(self) -> None:
        self._write_summary()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "loop-status-report",
                "--latest",
                "--improvement-runs-dir",
                str(self.temp_dir / "improvement-runs"),
                "--validation-runs-dir",
                str(self.temp_dir / "supervised-runs"),
                "--heartbeat-interval-minutes",
                "20",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("# Loop Status Report\n", completed.stdout)
        self.assertIn("- Loop: `unit-loop`", completed.stdout)
        self.assertIn("- Utilization: aggressive; overlap risk high; idle risk unknown.", completed.stdout)


if __name__ == "__main__":
    unittest.main()
