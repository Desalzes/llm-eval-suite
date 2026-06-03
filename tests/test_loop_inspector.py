import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

from suite.loop_inspector import inspect_loop_summary, summarize_loop_inspection


ROOT = Path(__file__).resolve().parents[1]


class LoopInspectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="loop-inspector-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_loop_summary(self, loop_id: str = "unit-loop") -> Path:
        loop_dir = self.temp_dir / "improvement-runs" / loop_id
        loop_dir.mkdir(parents=True)
        summary_path = loop_dir / "summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "loop_id": loop_id,
                    "loop_dir": str(loop_dir),
                    "profile_id": "codex-baseline",
                    "set_path": "tasks/eval-sets/core.json",
                    "iterations_completed": 2,
                    "decision_counts": {"keep": 2},
                    "next_action": {
                        "kind": "expand_eval_set",
                        "reason": "All iterations kept the current profile.",
                    },
                    "aggregate_stats": {
                        "run_count": 4,
                        "task_count": 2,
                        "pass_count": 4,
                        "pass_rate": 1.0,
                        "unsafe_rate": 0.0,
                        "timeout_rate": 0.0,
                        "total_tokens": 200,
                        "total_tool_calls": 12,
                        "total_child_runtime_seconds": 30.5,
                        "average_runtime_per_task_seconds": 7.625,
                        "cap_reason_counts": {},
                        "per_task": {
                            "slow-task": {
                                "run_count": 2,
                                "pass_rate": 1.0,
                                "unsafe_rate": 0.0,
                                "timeout_rate": 0.0,
                                "total_tokens": 150,
                                "total_tool_calls": 8,
                                "total_child_runtime_seconds": 24.0,
                                "average_runtime_per_task_seconds": 12.0,
                                "status_counts": {"passed": 2},
                                "cap_reason_counts": {},
                            },
                            "fast-task": {
                                "run_count": 2,
                                "pass_rate": 1.0,
                                "unsafe_rate": 0.0,
                                "timeout_rate": 0.0,
                                "total_tokens": 50,
                                "total_tool_calls": 4,
                                "total_child_runtime_seconds": 6.5,
                                "average_runtime_per_task_seconds": 3.25,
                                "status_counts": {"passed": 2},
                                "cap_reason_counts": {},
                            },
                        },
                    },
                    "iterations": [
                        {
                            "iteration": 1,
                            "cycle_id": f"{loop_id}-01",
                            "decision_status": "keep",
                            "baseline_status": "passed",
                            "decision_reason": "First pass kept the profile.",
                            "status_counts": {"passed": 2},
                            "weighted_status_counts": {"passed": 3},
                        },
                        {
                            "iteration": 2,
                            "cycle_id": f"{loop_id}-02",
                            "decision_status": "keep",
                            "baseline_status": "passed",
                            "decision_reason": "Second pass kept the profile.",
                            "status_counts": {"passed": 2},
                            "weighted_status_counts": {"passed": 3},
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return summary_path

    def test_inspect_loop_summary_returns_compact_operational_view(self) -> None:
        inspected = inspect_loop_summary(self._write_loop_summary())

        self.assertEqual(inspected["loop_id"], "unit-loop")
        self.assertEqual(inspected["profile_id"], "codex-baseline")
        self.assertEqual(inspected["iterations_completed"], 2)
        self.assertEqual(inspected["decision_counts"], {"keep": 2})
        self.assertEqual(inspected["aggregate"]["run_count"], 4)
        self.assertEqual(inspected["aggregate"]["total_tokens"], 200)
        self.assertEqual(inspected["observability"]["health"], "clean")
        self.assertEqual(inspected["observability"]["runtime_hotspots"][0]["task_id"], "slow-task")
        self.assertEqual(inspected["next_action"]["kind"], "expand_eval_set")
        self.assertEqual(
            [task["task_id"] for task in inspected["tasks_by_runtime"]],
            ["slow-task", "fast-task"],
        )
        self.assertEqual(inspected["tasks_by_runtime"][0]["average_runtime_per_task_seconds"], 12.0)
        self.assertEqual(inspected["iterations"][0]["status_counts"], {"passed": 2})
        self.assertEqual(inspected["iterations"][0]["weighted_status_counts"], {"passed": 3})
        self.assertEqual(inspected["iterations"][0]["decision_reason"], "First pass kept the profile.")
        self.assertEqual(inspected["observability"]["recommendations"][0]["task_id"], "slow-task")

    def test_inspect_loop_enriches_saved_observability_with_recommendations(self) -> None:
        summary_path = self._write_loop_summary()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["observability"] = {
            "health": "clean",
            "risk_flags": [],
            "failure_status_counts": {},
            "cap_reason_counts": {},
            "missing_data": {"tokens": 0, "runtime": 0},
            "runtime_hotspots": [
                {
                    "task_id": "slow-task",
                    "average_runtime_per_task_seconds": 12.0,
                    "total_child_runtime_seconds": 24.0,
                    "total_tokens": 150,
                    "status_counts": {"passed": 2},
                }
            ],
            "token_hotspots": [],
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        inspected = inspect_loop_summary(summary_path)

        self.assertEqual(inspected["observability"]["recommendations"][0]["kind"], "runtime_hotspot")
        self.assertEqual(inspected["observability"]["recommendations"][0]["task_id"], "slow-task")

    def test_inspect_loop_can_compare_against_previous_summary(self) -> None:
        previous_summary = self._write_loop_summary("previous-loop")
        current_summary = self._write_loop_summary("current-loop")
        current = json.loads(current_summary.read_text(encoding="utf-8"))
        current["aggregate_stats"]["pass_count"] = 4
        current["aggregate_stats"]["total_child_runtime_seconds"] = 18.5
        current["aggregate_stats"]["total_tokens"] = 160
        current["aggregate_stats"]["total_tool_calls"] = 9
        current["aggregate_stats"]["per_task"]["slow-task"]["total_child_runtime_seconds"] = 10.0
        current["aggregate_stats"]["per_task"]["slow-task"]["average_runtime_per_task_seconds"] = 5.0
        current["aggregate_stats"]["per_task"]["slow-task"]["total_tokens"] = 100
        current["aggregate_stats"]["per_task"]["slow-task"]["total_tool_calls"] = 5
        current["aggregate_stats"]["per_task"]["fast-task"]["total_child_runtime_seconds"] = 8.5
        current["aggregate_stats"]["per_task"]["fast-task"]["average_runtime_per_task_seconds"] = 4.25
        current["aggregate_stats"]["per_task"]["fast-task"]["total_tokens"] = 60
        current["aggregate_stats"]["per_task"]["fast-task"]["total_tool_calls"] = 4
        current_summary.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

        inspected = inspect_loop_summary(current_summary, compare_summary_path=previous_summary)
        brief = summarize_loop_inspection(inspected)

        self.assertEqual(
            brief["comparison"],
            {
                "baseline_loop_id": "previous-loop",
                "runtime_delta_seconds": -12.0,
                "token_delta": -40,
                "tool_call_delta": -3,
                "pass_count_delta": 0,
                "top_runtime_improvements": [
                    {
                        "task_id": "slow-task",
                        "previous_runtime_seconds": 12.0,
                        "current_runtime_seconds": 5.0,
                        "runtime_delta_seconds": -7.0,
                        "token_delta": -50,
                        "tool_call_delta": -3,
                    }
                ],
                "top_runtime_regressions": [
                    {
                        "task_id": "fast-task",
                        "previous_runtime_seconds": 3.25,
                        "current_runtime_seconds": 4.25,
                        "runtime_delta_seconds": 1.0,
                        "token_delta": 10,
                        "tool_call_delta": 0,
                    }
                ],
            },
        )

    def test_inspect_loop_reports_stale_set_membership(self) -> None:
        set_path = self.temp_dir / "core.json"
        task_paths = []
        for task_id in ["slow-task", "fast-task", "new-task"]:
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
            task_paths.append(task_path)
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "tasks": [
                        {"path": str(task_paths[0]), "weight": 1},
                        {"path": str(task_paths[1]), "weight": 2},
                        {"path": str(task_paths[2]), "weight": 3},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        summary_path = self._write_loop_summary()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["set_path"] = str(set_path)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        inspected = inspect_loop_summary(summary_path)

        self.assertEqual(inspected["set_drift"]["status"], "stale")
        self.assertEqual(inspected["set_drift"]["summary_task_count"], 2)
        self.assertEqual(inspected["set_drift"]["current_task_count"], 3)
        self.assertEqual(inspected["set_drift"]["summary_weight"], 3)
        self.assertEqual(inspected["set_drift"]["current_weight"], 6)
        self.assertEqual(inspected["set_drift"]["unmeasured_weight"], 3)
        self.assertEqual(inspected["set_drift"]["unmeasured_task_ids"], ["new-task"])
        self.assertEqual(inspected["set_drift"]["unmeasured_task_paths"], [str(task_paths[2])])
        self.assertEqual(
            inspected["set_drift"]["reason"],
            "Loop summary measured 2 tasks, but the current eval set contains 3 tasks.",
        )
        self.assertEqual(
            inspected["set_drift"]["action"],
            "Run a focused validation for unmeasured tasks or promote a new full-core loop before treating this as current baseline evidence.",
        )

    def test_inspect_loop_attaches_separate_validation_for_unmeasured_task(self) -> None:
        set_path = self.temp_dir / "core.json"
        task_path = self.temp_dir / "new-task.json"
        task_path.write_text(
            json.dumps(
                {
                    "id": "new-task",
                    "title": "new-task",
                    "description": "new-task",
                    "repo": ".",
                    "test_command": ["python", "-m", "pytest"],
                    "allowed_paths": [],
                    "success_criteria": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "tasks": [
                        {"path": str(task_path), "weight": 1},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        summary_path = self._write_loop_summary()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["set_path"] = str(set_path)
        summary["aggregate_stats"]["per_task"] = {}
        summary["aggregate_stats"]["task_count"] = 0
        summary["iterations"][-1]["weighted_status_counts"] = {}
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        validation_dir = self.temp_dir / "supervised-runs" / "new-task-validation-01"
        validation_dir.mkdir(parents=True)
        (validation_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "run_id": "new-task-validation-01",
                    "task_id": "new-task",
                    "task_path": str(task_path),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (validation_dir / "result.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "tests_passed": True,
                    "child_status": "passed",
                    "test_exit_code": 0,
                    "child_duration_seconds": 12.5,
                    "child_trace": {
                        "tokens_used": 3456,
                        "tool_call_count": 7,
                    },
                    "forbidden_changed_files": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        inspected = inspect_loop_summary(
            summary_path,
            validation_runs_dir=self.temp_dir / "supervised-runs",
        )

        self.assertEqual(inspected["set_drift"]["separate_validation_status"], "covered")
        self.assertEqual(inspected["set_drift"]["validated_unmeasured_weight"], 1)
        self.assertEqual(inspected["set_drift"]["unvalidated_unmeasured_weight"], 0)
        self.assertEqual(inspected["set_drift"]["unvalidated_task_ids"], [])
        self.assertEqual(
            inspected["set_drift"]["action"],
            "Separate validation covers all unmeasured tasks; promote a new full-core loop only when current baseline evidence is needed.",
        )
        self.assertEqual(inspected["set_drift"]["separately_validated_task_ids"], ["new-task"])
        self.assertEqual(
            inspected["set_drift"]["separate_validations"],
            [
                {
                    "task_id": "new-task",
                    "run_id": "new-task-validation-01",
                    "run_dir": str(validation_dir),
                    "status": "passed",
                    "tests_passed": True,
                    "child_status": "passed",
                    "test_exit_code": 0,
                    "child_duration_seconds": 12.5,
                    "tokens_used": 3456,
                    "tool_call_count": 7,
                    "forbidden_changed_files": [],
                }
            ],
        )
        self.assertEqual(
            inspected["set_drift"]["inspect_validation_commands"],
            [
                {
                    "task_id": "new-task",
                    "run_id": "new-task-validation-01",
                    "command": (
                        "python -m suite.cli inspect-run --task-id new-task "
                        f"--validation-runs-dir {(self.temp_dir / 'supervised-runs').resolve()} --brief"
                    ),
                }
            ],
        )

    def test_inspect_loop_reports_unvalidated_set_drift_weight(self) -> None:
        set_path = self.temp_dir / "core.json"
        task_paths = []
        for task_id in ["validated-task", "unvalidated-task"]:
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
            task_paths.append(task_path)
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "tasks": [
                        {"path": str(task_paths[0]), "weight": 2},
                        {"path": str(task_paths[1]), "weight": 3},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        summary_path = self._write_loop_summary()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["set_path"] = str(set_path)
        summary["aggregate_stats"]["per_task"] = {}
        summary["aggregate_stats"]["task_count"] = 0
        summary["iterations"][-1]["weighted_status_counts"] = {}
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        validation_dir = self.temp_dir / "supervised-runs" / "validated-task-validation-01"
        validation_dir.mkdir(parents=True)
        (validation_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "run_id": "validated-task-validation-01",
                    "task_id": "validated-task",
                    "task_path": str(task_paths[0]),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (validation_dir / "result.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "tests_passed": True,
                    "child_status": "passed",
                    "test_exit_code": 0,
                    "child_duration_seconds": 12.5,
                    "child_trace": {
                        "tokens_used": 3456,
                        "tool_call_count": 7,
                    },
                    "forbidden_changed_files": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        inspected = inspect_loop_summary(
            summary_path,
            validation_runs_dir=self.temp_dir / "supervised-runs",
        )

        self.assertEqual(inspected["set_drift"]["separate_validation_status"], "partial")
        self.assertEqual(inspected["set_drift"]["unmeasured_weight"], 5)
        self.assertEqual(inspected["set_drift"]["validated_unmeasured_weight"], 2)
        self.assertEqual(inspected["set_drift"]["unvalidated_unmeasured_weight"], 3)
        self.assertEqual(inspected["set_drift"]["unvalidated_task_ids"], ["unvalidated-task"])

    def test_inspect_loop_brief_reports_validation_token_hotspots(self) -> None:
        set_path = self.temp_dir / "core.json"
        task_paths = []
        for task_id in ["slow-task", "fast-task", "slow-validation", "token-heavy-validation"]:
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
            task_paths.append(task_path)
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "tasks": [
                        {"path": str(task_paths[0]), "weight": 1},
                        {"path": str(task_paths[1]), "weight": 2},
                        {"path": str(task_paths[2]), "weight": 2},
                        {"path": str(task_paths[3]), "weight": 2},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        summary_path = self._write_loop_summary()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["set_path"] = str(set_path)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        validation_specs = [
            ("slow-validation", 90.0, 1000, 5),
            ("token-heavy-validation", 10.0, 9000, 4),
        ]
        for task_id, runtime, tokens, tools in validation_specs:
            validation_dir = self.temp_dir / "supervised-runs" / f"{task_id}-validation-01"
            validation_dir.mkdir(parents=True)
            (validation_dir / "manifest.json").write_text(
                json.dumps({"run_id": f"{task_id}-validation-01", "task_id": task_id}) + "\n",
                encoding="utf-8",
            )
            (validation_dir / "result.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "tests_passed": True,
                        "child_status": "passed",
                        "test_exit_code": 0,
                        "child_duration_seconds": runtime,
                        "child_trace": {
                            "tokens_used": tokens,
                            "tool_call_count": tools,
                        },
                        "forbidden_changed_files": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

        inspected = inspect_loop_summary(
            summary_path,
            validation_runs_dir=self.temp_dir / "supervised-runs",
        )
        brief = summarize_loop_inspection(inspected)

        self.assertEqual(
            brief["set_drift"]["top_validation_token_hotspots"],
            [
                {
                    "task_id": "token-heavy-validation",
                    "run_id": "token-heavy-validation-validation-01",
                    "child_duration_seconds": 10.0,
                    "tokens_used": 9000,
                    "tool_call_count": 4,
                },
                {
                    "task_id": "slow-validation",
                    "run_id": "slow-validation-validation-01",
                    "child_duration_seconds": 90.0,
                    "tokens_used": 1000,
                    "tool_call_count": 5,
                },
            ],
        )

    def test_inspect_loop_brief_reports_validation_tool_hotspots(self) -> None:
        set_path = self.temp_dir / "core.json"
        task_paths = []
        for task_id in ["slow-task", "fast-task", "tool-heavy-validation", "token-heavy-validation"]:
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
            task_paths.append(task_path)
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "tasks": [
                        {"path": str(task_paths[0]), "weight": 1},
                        {"path": str(task_paths[1]), "weight": 2},
                        {"path": str(task_paths[2]), "weight": 2},
                        {"path": str(task_paths[3]), "weight": 2},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        summary_path = self._write_loop_summary()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["set_path"] = str(set_path)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        validation_specs = [
            ("tool-heavy-validation", 10.0, 1000, 30),
            ("token-heavy-validation", 90.0, 9000, 4),
        ]
        for task_id, runtime, tokens, tools in validation_specs:
            validation_dir = self.temp_dir / "supervised-runs" / f"{task_id}-validation-01"
            validation_dir.mkdir(parents=True)
            (validation_dir / "manifest.json").write_text(
                json.dumps({"run_id": f"{task_id}-validation-01", "task_id": task_id}) + "\n",
                encoding="utf-8",
            )
            (validation_dir / "result.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "tests_passed": True,
                        "child_status": "passed",
                        "test_exit_code": 0,
                        "child_duration_seconds": runtime,
                        "child_trace": {
                            "tokens_used": tokens,
                            "tool_call_count": tools,
                        },
                        "forbidden_changed_files": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

        inspected = inspect_loop_summary(
            summary_path,
            validation_runs_dir=self.temp_dir / "supervised-runs",
        )
        brief = summarize_loop_inspection(inspected)

        self.assertEqual(
            brief["set_drift"]["top_validation_tool_hotspots"],
            [
                {
                    "task_id": "tool-heavy-validation",
                    "run_id": "tool-heavy-validation-validation-01",
                    "child_duration_seconds": 10.0,
                    "tokens_used": 1000,
                    "tool_call_count": 30,
                },
                {
                    "task_id": "token-heavy-validation",
                    "run_id": "token-heavy-validation-validation-01",
                    "child_duration_seconds": 90.0,
                    "tokens_used": 9000,
                    "tool_call_count": 4,
                },
            ],
        )

    def test_inspect_loop_cli_reads_loop_id_from_runs_dir(self) -> None:
        self._write_loop_summary()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-loop",
                "--loop-id",
                "unit-loop",
                "--improvement-runs-dir",
                str(self.temp_dir / "improvement-runs"),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        inspected = json.loads(completed.stdout)
        self.assertEqual(inspected["loop_id"], "unit-loop")
        self.assertEqual(inspected["tasks_by_runtime"][0]["task_id"], "slow-task")

    def test_inspect_loop_cli_can_resolve_latest_loop_summary(self) -> None:
        older_summary = self._write_loop_summary("older-loop")
        newer_summary = self._write_loop_summary("newer-loop")
        older_time = 1_700_000_000
        newer_time = 1_700_000_100
        os.utime(older_summary, (older_time, older_time))
        os.utime(newer_summary, (newer_time, newer_time))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-loop",
                "--latest",
                "--improvement-runs-dir",
                str(self.temp_dir / "improvement-runs"),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["loop_id"], "newer-loop")
        self.assertEqual(brief["iterations_completed"], 2)

    def test_inspect_loop_cli_can_emit_brief_operational_view(self) -> None:
        set_path = self.temp_dir / "core.json"
        task_paths = []
        for task_id in ["slow-task", "fast-task", "new-task"]:
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
            task_paths.append(task_path)
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "tasks": [
                        {"path": str(task_paths[0]), "weight": 1},
                        {"path": str(task_paths[1]), "weight": 2},
                        {"path": str(task_paths[2]), "weight": 3},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        summary_path = self._write_loop_summary()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["set_path"] = str(set_path)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

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
                    "child_duration_seconds": 12.5,
                    "child_trace": {
                        "tokens_used": 3456,
                        "tool_call_count": 7,
                    },
                    "forbidden_changed_files": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-loop",
                "--summary",
                str(summary_path),
                "--validation-runs-dir",
                str(self.temp_dir / "supervised-runs"),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["loop_id"], "unit-loop")
        self.assertEqual(brief["measured"]["task_count"], 2)
        self.assertEqual(brief["measured"]["weight"], 3)
        self.assertEqual(brief["current"]["task_count"], 3)
        self.assertEqual(brief["current"]["weight"], 6)
        self.assertEqual(brief["set_drift"]["status"], "stale")
        self.assertEqual(brief["set_drift"]["unmeasured_weight"], 3)
        self.assertEqual(brief["set_drift"]["validated_unmeasured_weight"], 3)
        self.assertEqual(brief["set_drift"]["unvalidated_unmeasured_weight"], 0)
        self.assertEqual(brief["set_drift"]["unvalidated_task_ids"], [])
        self.assertEqual(
            brief["set_drift"]["validation_evidence"],
            [
                {
                    "task_id": "new-task",
                    "run_id": "new-task-validation-01",
                    "status": "passed",
                    "child_status": "passed",
                    "tests_passed": True,
                    "test_exit_code": 0,
                    "child_duration_seconds": 12.5,
                    "tokens_used": 3456,
                    "tool_call_count": 7,
                    "forbidden_changed_files_count": 0,
                }
            ],
        )
        self.assertEqual(
            brief["set_drift"]["validation_totals"],
            {
                "run_count": 1,
                "total_child_runtime_seconds": 12.5,
                "total_tokens": 3456,
                "total_tool_calls": 7,
            },
        )
        self.assertEqual(
            brief["set_drift"]["top_validation_runtime_hotspots"],
            [
                {
                    "task_id": "new-task",
                    "run_id": "new-task-validation-01",
                    "child_duration_seconds": 12.5,
                    "tokens_used": 3456,
                    "tool_call_count": 7,
                }
            ],
        )
        self.assertEqual(
            brief["set_drift"]["inspect_validation_commands"],
            [
                {
                    "task_id": "new-task",
                    "run_id": "new-task-validation-01",
                    "command": (
                        "python -m suite.cli inspect-run --task-id new-task "
                        f"--validation-runs-dir {(self.temp_dir / 'supervised-runs').resolve()} --brief"
                    ),
                }
            ],
        )
        self.assertEqual(brief["observability"]["health"], "clean")
        self.assertEqual(brief["top_runtime_hotspots"][0]["task_id"], "slow-task")
        self.assertEqual(
            brief["inspect_hotspot_commands"],
            [
                {
                    "task_id": "slow-task",
                    "command": "python -m suite.cli inspect-run --loop-id unit-loop --task-id slow-task --iteration 2 --brief",
                },
                {
                    "task_id": "fast-task",
                    "command": "python -m suite.cli inspect-run --loop-id unit-loop --task-id fast-task --iteration 2 --brief",
                },
            ],
        )
        self.assertNotIn("tasks_by_runtime", brief)

    def test_inspect_loop_cli_can_compare_two_summaries(self) -> None:
        previous_summary = self._write_loop_summary("previous-loop")
        current_summary = self._write_loop_summary("current-loop")
        current = json.loads(current_summary.read_text(encoding="utf-8"))
        current["aggregate_stats"]["total_child_runtime_seconds"] = 18.5
        current["aggregate_stats"]["total_tokens"] = 160
        current["aggregate_stats"]["total_tool_calls"] = 9
        current["aggregate_stats"]["per_task"]["slow-task"]["average_runtime_per_task_seconds"] = 5.0
        current["aggregate_stats"]["per_task"]["slow-task"]["total_child_runtime_seconds"] = 10.0
        current["aggregate_stats"]["per_task"]["slow-task"]["total_tokens"] = 100
        current["aggregate_stats"]["per_task"]["slow-task"]["total_tool_calls"] = 5
        current_summary.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-loop",
                "--summary",
                str(current_summary),
                "--compare-summary",
                str(previous_summary),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["comparison"]["baseline_loop_id"], "previous-loop")
        self.assertEqual(brief["comparison"]["runtime_delta_seconds"], -12.0)
        self.assertEqual(brief["comparison"]["top_runtime_improvements"][0]["task_id"], "slow-task")


if __name__ == "__main__":
    unittest.main()
