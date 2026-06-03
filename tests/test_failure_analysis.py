import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.failure_analysis import (
    inspect_run_failure,
    resolve_eval_set_task_run_dir,
    resolve_loop_task_run_dir,
    resolve_validation_task_run_dir,
)


ROOT = Path(__file__).resolve().parents[1]


class FailureAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="failure-analysis-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def test_inspects_failed_run_from_one_directory(self) -> None:
        run_dir = self.temp_dir / "run-tests-failed"
        child_dir = run_dir / "child"
        self._write_json(
            run_dir / "manifest.json",
            {
                "run_id": "run-tests-failed",
                "task_id": "python-cli-bugfix",
                "profile_id": "codex-baseline",
            },
        )
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "run-tests-failed",
                "status": "failed",
                "child_status": "passed",
                "child_cap_reason": None,
                "child_session_dir": str(child_dir),
                "child_exit_code": 0,
                "test_exit_code": 1,
                "tests_passed": False,
                "changed_files": ["calculator.py"],
                "forbidden_changed_files": [],
            },
        )
        self._write_json(child_dir / "result.json", {"status": "passed", "exit_code": 0})
        (child_dir / "transcript.txt").write_text("line a\nline b\nline c\n", encoding="utf-8")
        (run_dir / "test-output.txt").write_text("test one\nAssertionError: bad math\n", encoding="utf-8")
        (run_dir / "diff.patch").write_text("diff --git a/calculator.py b/calculator.py\n", encoding="utf-8")

        inspected = inspect_run_failure(run_dir, tail_lines=2)
        finding_path = run_dir / "findings.jsonl"
        finding = json.loads(finding_path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(inspected["run_id"], "run-tests-failed")
        self.assertEqual(inspected["task_id"], "python-cli-bugfix")
        self.assertEqual(inspected["status"], "failed")
        self.assertEqual(inspected["failure_class"], "tests_failed")
        self.assertEqual(inspected["findings"], [finding])
        self.assertEqual(finding["schema_version"], "finding_v1")
        self.assertEqual(finding["detector_id"], "suite.inspect_run")
        self.assertEqual(finding["artifact_id"], "run-tests-failed")
        self.assertEqual(finding["finding_type"], "tests_failed")
        self.assertEqual(finding["severity"], "medium")
        self.assertEqual(finding["confidence"], "high")
        self.assertEqual(finding["required_approval_tier"], "human_review")
        self.assertIn(str(run_dir / "test-output.txt"), finding["affected_artifacts"])
        self.assertEqual(inspected["primary_reason"], "Task verification failed after the child session.")
        self.assertEqual(
            inspected["recommended_actions"],
            [
                "Read test_output_tail first; it contains the verifier failure.",
                "Inspect diff.patch to compare the child edit against the failing assertion.",
                "If the failure is unclear, open the child transcript around the final verification command.",
            ],
        )
        self.assertEqual(inspected["checks"]["test_exit_code"], 1)
        self.assertEqual(inspected["checks"]["child_status"], "passed")
        self.assertEqual(inspected["changed_files"], ["calculator.py"])
        self.assertEqual(inspected["forbidden_changed_files"], [])
        self.assertTrue(inspected["artifacts"]["result"].endswith("result.json"))
        self.assertTrue(inspected["artifacts"]["child_transcript"].endswith("transcript.txt"))
        self.assertEqual(inspected["excerpts"]["test_output_tail"], "test one\nAssertionError: bad math")
        self.assertEqual(inspected["excerpts"]["child_transcript_tail"], "line b\nline c")

    def test_keeps_child_timeout_distinct_from_child_failure(self) -> None:
        run_dir = self.temp_dir / "run-child-timeout"
        child_dir = run_dir / "child"
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "run-child-timeout",
                "run_dir": str(run_dir),
                "status": "failed",
                "child_status": "timeout",
                "child_cap_reason": "timeout_seconds",
                "child_session_dir": str(child_dir),
                "child_exit_code": 1,
                "test_exit_code": 1,
                "tests_passed": False,
                "changed_files": [],
                "forbidden_changed_files": [],
            },
        )
        (child_dir / "transcript.txt").parent.mkdir(parents=True)
        (child_dir / "transcript.txt").write_text("still working\n", encoding="utf-8")

        inspected = inspect_run_failure(run_dir)

        self.assertEqual(inspected["failure_class"], "child_timeout")
        self.assertEqual(inspected["primary_reason"], "Child session hit the wall-clock timeout cap.")
        self.assertEqual(
            inspected["recommended_actions"],
            [
                "Inspect child_transcript_tail to see the last active operation before timeout.",
                "Check child_events for the timeout event and output cadence.",
                "Treat this as a process/runtime issue unless the transcript shows a model decision problem.",
            ],
        )
        self.assertEqual(inspected["checks"]["child_cap_reason"], "timeout_seconds")

    def test_identifies_child_timeout_after_validation_passed(self) -> None:
        run_dir = self.temp_dir / "run-timeout-after-validation"
        child_dir = run_dir / "child"
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "run-timeout-after-validation",
                "run_dir": str(run_dir),
                "status": "failed",
                "child_status": "timeout",
                "child_cap_reason": "timeout_seconds",
                "child_session_dir": str(child_dir),
                "child_exit_code": 1,
                "test_exit_code": 0,
                "tests_passed": True,
                "changed_files": ["skills/csv-normalization/SKILL.md"],
                "forbidden_changed_files": [],
            },
        )
        (child_dir / "transcript.txt").parent.mkdir(parents=True)
        (child_dir / "transcript.txt").write_text("final status check\n", encoding="utf-8")

        inspected = inspect_run_failure(run_dir)

        self.assertEqual(inspected["failure_class"], "child_timeout_after_validation")
        self.assertEqual(inspected["primary_reason"], "Child session hit the timeout cap after task verification passed.")
        self.assertEqual(
            inspected["recommended_actions"],
            [
                "Treat the child edit as validation-covered before changing task criteria.",
                "Inspect child_transcript_tail and child_events for finalization or repeated-output noise.",
                "Consider a higher child timeout for promotion runs if focused validation passes.",
            ],
        )
        self.assertEqual(inspected["checks"]["tests_passed"], True)

    def test_identifies_child_auth_failure_from_transcript(self) -> None:
        run_dir = self.temp_dir / "run-child-auth-failure"
        child_dir = run_dir / "child"
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "run-child-auth-failure",
                "run_dir": str(run_dir),
                "status": "failed",
                "child_status": "failed",
                "child_session_dir": str(child_dir),
                "child_exit_code": 1,
                "test_exit_code": 1,
                "tests_passed": False,
                "changed_files": [],
                "forbidden_changed_files": [],
            },
        )
        (child_dir / "transcript.txt").parent.mkdir(parents=True)
        (child_dir / "transcript.txt").write_text(
            "\n".join(
                [
                    "ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized",
                    "WARN codex_core::session::turn: stream disconnected - retrying sampling request (5/5)",
                    "ERROR: stream disconnected before completion: error sending request for url (https://api.openai.com/v1/responses)",
                ]
            ),
            encoding="utf-8",
        )

        inspected = inspect_run_failure(run_dir)

        self.assertEqual(inspected["failure_class"], "child_auth_failure")
        self.assertEqual(inspected["primary_reason"], "Child session could not authenticate with the model provider.")
        self.assertEqual(
            inspected["recommended_actions"],
            [
                "Fix child-session provider authentication before changing tasks, prompts, or skills.",
                "Check OPENAI_API_KEY / bearer-token configuration for the child profile and rerun a smoke task.",
                "Treat affected eval results as infrastructure failures, not model or task regressions.",
            ],
        )

    def test_inspect_run_cli_prints_json_summary(self) -> None:
        run_dir = self.temp_dir / "cli-run"
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "cli-run",
                "status": "unsafe",
                "child_status": "passed",
                "child_exit_code": 0,
                "test_exit_code": 0,
                "tests_passed": True,
                "changed_files": ["blocked.txt"],
                "forbidden_changed_files": ["blocked.txt"],
            },
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--run-dir",
                str(run_dir),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        inspected = json.loads(completed.stdout)
        self.assertEqual(inspected["failure_class"], "unsafe_edit")
        self.assertEqual(inspected["primary_reason"], "Run changed files outside the allowed path set.")
        self.assertEqual(inspected["recommended_actions"][0], "Review forbidden_changed_files before reading the diff.")

    def test_inspect_run_cli_can_emit_brief_failure_view(self) -> None:
        run_dir = self.temp_dir / "cli-run-tests-failed"
        child_dir = run_dir / "child"
        self._write_json(
            run_dir / "manifest.json",
            {
                "run_id": "cli-run-tests-failed",
                "task_id": "python-cli-bugfix",
                "profile_id": "codex-baseline",
            },
        )
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "cli-run-tests-failed",
                "status": "failed",
                "child_status": "passed",
                "child_session_dir": str(child_dir),
                "child_exit_code": 0,
                "test_exit_code": 1,
                "tests_passed": False,
                "changed_files": ["calculator.py", "tests/test_calculator.py"],
                "forbidden_changed_files": [],
            },
        )
        self._write_json(child_dir / "result.json", {"status": "passed", "exit_code": 0})
        (child_dir / "transcript.txt").write_text("child line a\nchild line b\n", encoding="utf-8")
        (run_dir / "test-output.txt").write_text("pytest line\nAssertionError: bad math\n", encoding="utf-8")
        (run_dir / "diff.patch").write_text("diff --git a/calculator.py b/calculator.py\n", encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--run-dir",
                str(run_dir),
                "--tail-lines",
                "2",
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["run_id"], "cli-run-tests-failed")
        self.assertEqual(brief["task_id"], "python-cli-bugfix")
        self.assertEqual(brief["status"], "failed")
        self.assertEqual(brief["failure_class"], "tests_failed")
        self.assertEqual(brief["checks"]["test_exit_code"], 1)
        self.assertEqual(brief["changed_files_count"], 2)
        self.assertEqual(brief["forbidden_changed_files"], [])
        self.assertEqual(brief["next_action"], "Read test_output_tail first; it contains the verifier failure.")
        self.assertEqual(
            brief["key_excerpt"],
            {
                "source": "test_output_tail",
                "text": "pytest line\nAssertionError: bad math",
            },
        )
        self.assertTrue(brief["key_artifacts"]["test_output"].endswith("test-output.txt"))
        self.assertTrue(brief["key_artifacts"]["diff"].endswith("diff.patch"))
        self.assertNotIn("excerpts", brief)
        self.assertNotIn("changed_files", brief)

    def test_inspect_run_brief_includes_child_trace_diagnostics(self) -> None:
        run_dir = self.temp_dir / "cli-run-passed"
        child_dir = run_dir / "child"
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "cli-run-passed",
                "task_id": "temporal-cutoff-boundary",
                "status": "passed",
                "child_status": "passed",
                "child_session_dir": str(child_dir),
                "child_exit_code": 0,
                "test_exit_code": 0,
                "tests_passed": True,
                "changed_files": ["src/billing/pause_policy.py"],
                "forbidden_changed_files": [],
            },
        )
        self._write_json(
            child_dir / "trace-summary.json",
            {
                "tool_call_count": 15,
                "tokens_used": 56560,
                "startup_warning_count": 2,
                "remote_plugin_sync_warning_count": 1,
                "skill_file_read_count": 4,
                "patch_attempt_count": 2,
                "pytest_session_count": 3,
                "pytest_failed_test_marker_count": 5,
            },
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--run-dir",
                str(run_dir),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["failure_class"], "passed")
        self.assertEqual(
            brief["child_trace"],
            {
                "tool_call_count": 15,
                "tokens_used": 56560,
                "startup_warning_count": 2,
                "remote_plugin_sync_warning_count": 1,
                "skill_file_read_count": 4,
                "patch_attempt_count": 2,
                "pytest_session_count": 3,
                "pytest_failed_test_marker_count": 5,
            },
        )

    def test_inspect_run_enriches_older_trace_summary_from_transcript(self) -> None:
        run_dir = self.temp_dir / "cli-run-old-trace"
        child_dir = run_dir / "child"
        self._write_json(
            run_dir / "result.json",
            {
                "run_id": "cli-run-old-trace",
                "status": "passed",
                "child_status": "passed",
                "child_session_dir": str(child_dir),
                "tests_passed": True,
                "test_exit_code": 0,
                "forbidden_changed_files": [],
            },
        )
        self._write_json(child_dir / "trace-summary.json", {"tool_call_count": 1})
        (child_dir / "transcript.txt").write_text(
            """=== child output ===
2026-05-14T16:36:37.082049Z  WARN codex_core_plugins::startup_remote_sync: remote plugin sync request failed
OpenAI Codex v0.130.0
exec
apply patch
============================= test session starts =============================
""",
            encoding="utf-8",
        )

        inspected = inspect_run_failure(run_dir)

        self.assertEqual(inspected["child_trace"]["tool_call_count"], 1)
        self.assertEqual(inspected["child_trace"]["startup_warning_count"], 1)
        self.assertEqual(inspected["child_trace"]["remote_plugin_sync_warning_count"], 1)
        self.assertEqual(inspected["child_trace"]["patch_attempt_count"], 1)
        self.assertEqual(inspected["child_trace"]["pytest_session_count"], 1)

    def test_resolves_task_run_directory_from_loop_id_and_task_id(self) -> None:
        loop_dir = self.temp_dir / "improvement-runs" / "unit-loop"
        task_run_dir = loop_dir / "eval-runs" / "unit-loop-02-baseline" / "tasks" / "03-target-task"
        task_run_dir.mkdir(parents=True)
        self._write_json(
            loop_dir / "summary.json",
            {
                "loop_id": "unit-loop",
                "iterations": [
                    {"iteration": 1, "cycle_id": "unit-loop-01"},
                    {"iteration": 2, "cycle_id": "unit-loop-02"},
                ],
            },
        )

        resolved = resolve_loop_task_run_dir(
            loop_id="unit-loop",
            task_id="target-task",
            improvement_runs_dir=self.temp_dir / "improvement-runs",
        )

        self.assertEqual(resolved, task_run_dir.resolve())

    def test_resolves_task_run_directory_from_specific_iteration(self) -> None:
        loop_dir = self.temp_dir / "improvement-runs" / "unit-loop"
        first_task_run_dir = loop_dir / "eval-runs" / "unit-loop-01-baseline" / "tasks" / "03-target-task"
        second_task_run_dir = loop_dir / "eval-runs" / "unit-loop-02-baseline" / "tasks" / "03-target-task"
        first_task_run_dir.mkdir(parents=True)
        second_task_run_dir.mkdir(parents=True)
        self._write_json(
            loop_dir / "summary.json",
            {
                "loop_id": "unit-loop",
                "iterations": [
                    {"iteration": 1, "cycle_id": "unit-loop-01"},
                    {"iteration": 2, "cycle_id": "unit-loop-02"},
                ],
            },
        )

        resolved = resolve_loop_task_run_dir(
            loop_id="unit-loop",
            task_id="target-task",
            improvement_runs_dir=self.temp_dir / "improvement-runs",
            iteration=1,
        )

        self.assertEqual(resolved, first_task_run_dir.resolve())

    def test_inspect_run_cli_accepts_loop_id_and_task_id(self) -> None:
        loop_dir = self.temp_dir / "improvement-runs" / "unit-loop"
        task_run_dir = loop_dir / "eval-runs" / "unit-loop-01-baseline" / "tasks" / "02-target-task"
        self._write_json(loop_dir / "summary.json", {"loop_id": "unit-loop", "iterations": [{"cycle_id": "unit-loop-01"}]})
        self._write_json(
            task_run_dir / "result.json",
            {
                "run_id": "02-target-task",
                "task_id": "target-task",
                "status": "failed",
                "child_status": "passed",
                "child_exit_code": 0,
                "test_exit_code": 1,
                "tests_passed": False,
                "changed_files": [],
                "forbidden_changed_files": [],
            },
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--loop-id",
                "unit-loop",
                "--task-id",
                "target-task",
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
        self.assertEqual(inspected["task_id"], "target-task")
        self.assertEqual(inspected["failure_class"], "tests_failed")

    def test_inspect_run_cli_accepts_specific_iteration(self) -> None:
        loop_dir = self.temp_dir / "improvement-runs" / "unit-loop"
        first_task_run_dir = loop_dir / "eval-runs" / "unit-loop-01-baseline" / "tasks" / "02-target-task"
        second_task_run_dir = loop_dir / "eval-runs" / "unit-loop-02-baseline" / "tasks" / "02-target-task"
        self._write_json(
            loop_dir / "summary.json",
            {
                "loop_id": "unit-loop",
                "iterations": [
                    {"iteration": 1, "cycle_id": "unit-loop-01"},
                    {"iteration": 2, "cycle_id": "unit-loop-02"},
                ],
            },
        )
        self._write_json(
            first_task_run_dir / "result.json",
            {
                "run_id": "02-target-task",
                "task_id": "target-task",
                "status": "failed",
                "child_status": "passed",
                "child_exit_code": 0,
                "test_exit_code": 1,
                "tests_passed": False,
            },
        )
        self._write_json(
            second_task_run_dir / "result.json",
            {
                "run_id": "02-target-task",
                "task_id": "target-task",
                "status": "unsafe",
                "forbidden_changed_files": ["blocked.txt"],
            },
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--loop-id",
                "unit-loop",
                "--task-id",
                "target-task",
                "--iteration",
                "1",
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
        self.assertEqual(inspected["failure_class"], "tests_failed")

    def test_resolves_task_run_directory_from_eval_set_run_id_and_task_id(self) -> None:
        eval_run_dir = self.temp_dir / "eval-runs" / "unit-smoke"
        task_run_dir = eval_run_dir / "tasks" / "02-target-task"
        self._write_json(
            eval_run_dir / "summary.json",
            {
                "run_id": "unit-smoke",
                "set_id": "smoke",
                "runs": [
                    {
                        "task_id": "other-task",
                        "run_dir": str(eval_run_dir / "tasks" / "01-other-task"),
                    },
                    {
                        "task_id": "target-task",
                        "run_dir": str(task_run_dir),
                    },
                ],
            },
        )
        task_run_dir.mkdir(parents=True)

        resolved = resolve_eval_set_task_run_dir(
            eval_set_run_id="unit-smoke",
            task_id="target-task",
            eval_runs_dir=self.temp_dir / "eval-runs",
        )

        self.assertEqual(resolved, task_run_dir.resolve())

    def test_inspect_run_cli_accepts_eval_set_run_id_and_task_id(self) -> None:
        eval_run_dir = self.temp_dir / "eval-runs" / "unit-smoke"
        task_run_dir = eval_run_dir / "tasks" / "02-target-task"
        self._write_json(
            eval_run_dir / "summary.json",
            {
                "run_id": "unit-smoke",
                "set_id": "smoke",
                "runs": [
                    {
                        "task_id": "target-task",
                        "run_dir": str(task_run_dir),
                    }
                ],
            },
        )
        self._write_json(
            task_run_dir / "result.json",
            {
                "run_id": "02-target-task",
                "task_id": "target-task",
                "status": "failed",
                "child_status": "passed",
                "child_exit_code": 0,
                "test_exit_code": 1,
                "tests_passed": False,
                "changed_files": [],
                "forbidden_changed_files": [],
            },
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--eval-set-run-id",
                "unit-smoke",
                "--task-id",
                "target-task",
                "--eval-runs-dir",
                str(self.temp_dir / "eval-runs"),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        brief = json.loads(completed.stdout)
        self.assertEqual(brief["run_id"], "02-target-task")
        self.assertEqual(brief["task_id"], "target-task")
        self.assertEqual(brief["failure_class"], "tests_failed")

    def test_inspect_run_cli_accepts_latest_eval_set_id_and_task_id(self) -> None:
        eval_runs_dir = self.temp_dir / "eval-runs"
        for run_id, status, timestamp in [
            ("older-smoke", "unsafe", 1_700_000_000),
            ("newer-smoke", "failed", 1_700_000_100),
        ]:
            eval_run_dir = eval_runs_dir / run_id
            task_run_dir = eval_run_dir / "tasks" / "02-target-task"
            self._write_json(
                eval_run_dir / "summary.json",
                {
                    "run_id": run_id,
                    "set_id": "smoke",
                    "runs": [
                        {
                            "task_id": "target-task",
                            "run_dir": str(task_run_dir),
                        }
                    ],
                },
            )
            self._write_json(
                task_run_dir / "result.json",
                {
                    "run_id": "02-target-task",
                    "task_id": "target-task",
                    "status": status,
                    "child_status": "passed",
                    "child_exit_code": 0,
                    "test_exit_code": 1,
                    "tests_passed": False,
                    "changed_files": [],
                    "forbidden_changed_files": ["blocked.txt"] if status == "unsafe" else [],
                },
            )
            os.utime(eval_run_dir / "summary.json", (timestamp, timestamp))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--set-id",
                "smoke",
                "--latest",
                "--task-id",
                "target-task",
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
        self.assertEqual(brief["run_id"], "02-target-task")
        self.assertEqual(brief["task_id"], "target-task")
        self.assertEqual(brief["status"], "failed")
        self.assertEqual(brief["failure_class"], "tests_failed")

    def test_resolves_validation_run_directory_from_task_id(self) -> None:
        validation_dir = self.temp_dir / "supervised-runs" / "target-task-validation-01"
        self._write_json(
            validation_dir / "manifest.json",
            {
                "run_id": "target-task-validation-01",
                "task_id": "target-task",
            },
        )
        self._write_json(validation_dir / "result.json", {"status": "passed"})

        resolved = resolve_validation_task_run_dir(
            task_id="target-task",
            validation_runs_dir=self.temp_dir / "supervised-runs",
        )

        self.assertEqual(resolved, validation_dir.resolve())

    def test_inspect_run_cli_accepts_validation_task_id(self) -> None:
        validation_dir = self.temp_dir / "supervised-runs" / "target-task-validation-01"
        self._write_json(
            validation_dir / "manifest.json",
            {
                "run_id": "target-task-validation-01",
                "task_id": "target-task",
            },
        )
        self._write_json(
            validation_dir / "result.json",
            {
                "run_id": "target-task-validation-01",
                "status": "passed",
                "tests_passed": True,
                "child_status": "passed",
                "test_exit_code": 0,
                "forbidden_changed_files": [],
            },
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-run",
                "--task-id",
                "target-task",
                "--validation-runs-dir",
                str(self.temp_dir / "supervised-runs"),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        inspected = json.loads(completed.stdout)
        self.assertEqual(inspected["run_id"], "target-task-validation-01")
        self.assertEqual(inspected["task_id"], "target-task")
        self.assertEqual(inspected["failure_class"], "passed")


if __name__ == "__main__":
    unittest.main()
