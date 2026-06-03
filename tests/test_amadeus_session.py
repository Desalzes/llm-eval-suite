import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class AmadeusSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="amadeus-session-test-"))
        self._write_required_files(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_required_files(self, root: Path) -> None:
        (root / "docs" / "superpowers" / "specs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "superpowers" / "plans").mkdir(parents=True, exist_ok=True)
        (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
        (root / "README.md").write_text("# Project\n", encoding="utf-8")
        (root / "docs" / "session-handoff.md").write_text("# Handoff\nCurrent status.\n", encoding="utf-8")
        (root / "docs" / "master-session-contract.md").write_text("# Master\n", encoding="utf-8")
        (root / "docs" / "workflow-stack.md").write_text("# Workflow\n", encoding="utf-8")
        (root / "docs" / "superpowers" / "specs" / "2026-05-26-amadeus-session-start-design.md").write_text(
            "# Amadeus Session Start Design\n",
            encoding="utf-8",
        )
        (root / "docs" / "superpowers" / "plans" / "2026-05-26-amadeus-session-start.md").write_text(
            "# Amadeus Session Start Implementation Plan\n",
            encoding="utf-8",
        )

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
                    "iterations_completed": 1,
                    "decision_counts": {"keep": 1},
                    "next_action": {
                        "kind": "keep_profile",
                        "reason": "Completed cleanly.",
                    },
                    "aggregate_stats": {
                        "run_count": 2,
                        "task_count": 2,
                        "pass_count": 2,
                        "pass_rate": 1.0,
                        "unsafe_rate": 0.0,
                        "timeout_rate": 0.0,
                        "total_tokens": 1200,
                        "total_tool_calls": 12,
                        "total_child_runtime_seconds": 50.0,
                        "average_runtime_per_task_seconds": 25.0,
                        "cap_reason_counts": {},
                        "per_task": {
                            "slow-task": {
                                "run_count": 1,
                                "pass_rate": 1.0,
                                "unsafe_rate": 0.0,
                                "timeout_rate": 0.0,
                                "total_tokens": 900,
                                "total_tool_calls": 9,
                                "total_child_runtime_seconds": 40.0,
                                "average_runtime_per_task_seconds": 40.0,
                                "status_counts": {"passed": 1},
                                "cap_reason_counts": {},
                            },
                            "cheap-task": {
                                "run_count": 1,
                                "pass_rate": 1.0,
                                "unsafe_rate": 0.0,
                                "timeout_rate": 0.0,
                                "total_tokens": 300,
                                "total_tool_calls": 3,
                                "total_child_runtime_seconds": 10.0,
                                "average_runtime_per_task_seconds": 10.0,
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
                        "runtime_hotspots": [
                            {
                                "task_id": "slow-task",
                                "average_runtime_per_task_seconds": 40.0,
                                "total_child_runtime_seconds": 40.0,
                                "total_tokens": 900,
                            }
                        ],
                        "token_hotspots": [
                            {
                                "task_id": "slow-task",
                                "total_tokens": 900,
                                "average_runtime_per_task_seconds": 40.0,
                            }
                        ],
                        "tool_call_hotspots": [
                            {
                                "task_id": "slow-task",
                                "total_tool_calls": 9,
                                "average_runtime_per_task_seconds": 40.0,
                            }
                        ],
                        "recommendations": [],
                    },
                    "iterations": [
                        {
                            "iteration": 1,
                            "cycle_id": f"{loop_id}-01",
                            "decision_status": "keep",
                            "baseline_status": "passed",
                            "decision_reason": "Completed cleanly.",
                            "status_counts": {"passed": 2},
                            "weighted_status_counts": {"passed": 2},
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return summary_path

    def _write_malformed_completed_loop_summary(self, loop_id: str = "bad-loop") -> Path:
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
                    "iterations_completed": 1,
                    "decision_counts": {"keep": 1},
                    "next_action": {"kind": "keep_profile"},
                    "aggregate_stats": {
                        "run_count": 1,
                        "task_count": 1,
                        "pass_count": 1,
                        "pass_rate": 1.0,
                        "unsafe_rate": 0.0,
                        "timeout_rate": 0.0,
                        "total_tokens": 10,
                        "total_tool_calls": 1,
                        "total_child_runtime_seconds": 1.0,
                        "average_runtime_per_task_seconds": 1.0,
                        "cap_reason_counts": {},
                        "per_task": [],
                    },
                    "iterations": [
                        {
                            "iteration": 1,
                            "cycle_id": f"{loop_id}-01",
                            "decision_status": "keep",
                            "baseline_status": "passed",
                            "status_counts": {"passed": 1},
                            "weighted_status_counts": {"passed": 1},
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return summary_path

    def _write_validation_hotspot_loop_summary(self, loop_id: str = "validation-hotspots") -> Path:
        tasks_dir = self.temp_dir / "tasks"
        set_dir = tasks_dir / "eval-sets"
        set_dir.mkdir(parents=True)
        task_ids = [
            "runtime-heavy",
            "middle-runtime",
            "steady-runtime",
            "token-heavy",
            "tool-heavy",
            "token-tool-heavy-validation",
        ]
        for task_id in task_ids:
            (tasks_dir / f"{task_id}.json").write_text(json.dumps({"id": task_id}) + "\n", encoding="utf-8")
        (set_dir / "core.json").write_text(
            json.dumps(
                {
                    "tasks": [
                        {"path": f"../{task_id}.json", "weight": 1}
                        for task_id in task_ids
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )

        summary_path = self._write_loop_summary(loop_id)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["set_path"] = str(set_dir / "core.json")
        summary["aggregate_stats"]["task_count"] = 5
        summary["aggregate_stats"]["per_task"] = {
            "runtime-heavy": {
                "run_count": 1,
                "pass_rate": 1.0,
                "unsafe_rate": 0.0,
                "timeout_rate": 0.0,
                "total_tokens": 100,
                "total_tool_calls": 2,
                "total_child_runtime_seconds": 50.0,
                "average_runtime_per_task_seconds": 50.0,
                "status_counts": {"passed": 1},
                "cap_reason_counts": {},
            },
            "middle-runtime": {
                "run_count": 1,
                "pass_rate": 1.0,
                "unsafe_rate": 0.0,
                "timeout_rate": 0.0,
                "total_tokens": 200,
                "total_tool_calls": 4,
                "total_child_runtime_seconds": 35.0,
                "average_runtime_per_task_seconds": 35.0,
                "status_counts": {"passed": 1},
                "cap_reason_counts": {},
            },
            "steady-runtime": {
                "run_count": 1,
                "pass_rate": 1.0,
                "unsafe_rate": 0.0,
                "timeout_rate": 0.0,
                "total_tokens": 300,
                "total_tool_calls": 5,
                "total_child_runtime_seconds": 25.0,
                "average_runtime_per_task_seconds": 25.0,
                "status_counts": {"passed": 1},
                "cap_reason_counts": {},
            },
            "token-heavy": {
                "run_count": 1,
                "pass_rate": 1.0,
                "unsafe_rate": 0.0,
                "timeout_rate": 0.0,
                "total_tokens": 9000,
                "total_tool_calls": 1,
                "total_child_runtime_seconds": 1.0,
                "average_runtime_per_task_seconds": 1.0,
                "status_counts": {"passed": 1},
                "cap_reason_counts": {},
            },
            "tool-heavy": {
                "run_count": 1,
                "pass_rate": 1.0,
                "unsafe_rate": 0.0,
                "timeout_rate": 0.0,
                "total_tokens": 50,
                "total_tool_calls": 80,
                "total_child_runtime_seconds": 2.0,
                "average_runtime_per_task_seconds": 2.0,
                "status_counts": {"passed": 1},
                "cap_reason_counts": {},
            },
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        validation_dir = self.temp_dir / "supervised-runs" / "token-tool-heavy-validation-01"
        validation_dir.mkdir(parents=True)
        (validation_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "task_id": "token-tool-heavy-validation",
                    "run_id": "validation-01",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (validation_dir / "result.json").write_text(
            json.dumps(
                {
                    "run_id": "validation-01",
                    "status": "passed",
                    "tests_passed": True,
                    "child_status": "passed",
                    "test_exit_code": 0,
                    "child_duration_seconds": 2.0,
                    "child_trace": {
                        "tokens_used": 5000,
                        "tool_call_count": 30,
                    },
                    "forbidden_changed_files": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return summary_path

    def test_amadeus_session_schema_is_registered(self) -> None:
        from suite.contracts import validate_contract

        manifest = {
            "schema_version": "amadeus_session_v1",
            "session_id": "amadeus-unit",
            "created_at": "2026-05-26T00:00:00Z",
            "updated_at": "2026-05-26T00:00:00Z",
            "repo_root": str(self.temp_dir),
            "status": "fast_ready",
            "git_snapshot": {
                "branch": None,
                "head": None,
                "status_lines": [],
                "recent_commits": [],
            },
            "fast_brief": {
                "status": "complete",
                "path": "fast-brief.json",
                "generated_at": "2026-05-26T00:00:00Z",
            },
            "deep_refresh": {
                "status": "not_started",
                "path": "deep-refresh.json",
                "command": "python -m suite.cli amadeus refresh --session-id amadeus-unit --deep",
                "started_at": None,
                "completed_at": None,
                "process_id": None,
                "stdout_path": None,
                "stderr_path": None,
                "error": None,
            },
            "live_checks": {
                "network": False,
                "ssh": False,
                "browser": False,
                "api": False,
                "service_status": False,
            },
            "artifacts": [
                "manifest.json",
                "fast-brief.json",
                "fast-brief.md",
                "conversation-brief.md",
            ],
        }

        self.assertEqual(validate_contract("amadeus-session", manifest), [])

    def test_start_session_writes_fast_brief_and_manifest(self) -> None:
        from suite.amadeus_session import start_session

        summary = start_session(
            self.temp_dir,
            session_id="amadeus-fast",
            fast=True,
            background_deep=False,
            force=True,
        )

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-fast"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))
        fast_brief = json.loads((session_dir / "fast-brief.json").read_text(encoding="utf-8"))
        conversation_brief = (session_dir / "conversation-brief.md").read_text(encoding="utf-8")

        self.assertEqual(summary["status"], "fast_ready")
        self.assertEqual(manifest["schema_version"], "amadeus_session_v1")
        self.assertEqual(manifest["session_id"], "amadeus-fast")
        self.assertEqual(manifest["fast_brief"]["status"], "complete")
        self.assertEqual(manifest["deep_refresh"]["status"], "not_started")
        self.assertFalse(any(manifest["live_checks"].values()))
        self.assertEqual(fast_brief["session_id"], "amadeus-fast")
        self.assertEqual(fast_brief["handoff"]["status"], "present")
        self.assertIn("Amadeus is ready", conversation_brief)
        self.assertTrue((session_dir / "fast-brief.md").exists())

    def test_start_session_includes_recent_conversation_memory(self) -> None:
        from suite.amadeus_session import start_session
        from suite.conversation_memory import append_memory

        append_memory(
            self.temp_dir,
            summary="Discussed Polymarket accounting, official account reconciliation, and dashboard PnL.",
            topics=["accounting", "polymarket"],
            source="assistant",
        )

        start_session(
            self.temp_dir,
            session_id="amadeus-memory",
            fast=True,
            background_deep=False,
            force=True,
        )

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-memory"
        fast_brief = json.loads((session_dir / "fast-brief.json").read_text(encoding="utf-8"))
        conversation_brief = (session_dir / "conversation-brief.md").read_text(encoding="utf-8")

        self.assertEqual(fast_brief["conversation_memory"]["status"], "present")
        self.assertIn("accounting", fast_brief["conversation_memory"]["entries"][0]["topics"])
        self.assertIn("official account reconciliation", conversation_brief)

    def test_start_executive_session_reads_memory_and_report_index_without_required_repo_docs(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job
        from suite.amadeus_session import start_executive_session
        from suite.conversation_memory import append_memory

        isolated = self.temp_dir / "isolated-executive"
        isolated.mkdir()
        append_memory(
            isolated,
            summary="User wants Amadeus to stay high-level and use worker reports for project truth.",
            topics=["amadeus", "delegation"],
            source="user",
        )
        job_id = "amadeus-job-20260531-121000"
        created = create_delegation_job(
            isolated,
            user_request="What is the state of the rebuild?",
            requested_output="status_report",
            job_id=job_id,
        )
        report = {
            "schema_version": "amadeus_worker_report_v1",
            "job_id": job_id,
            "created_at": "2026-05-31T12:10:00Z",
            "role": "investigator",
            "request": "What is the state of the rebuild?",
            "scope_decision": {
                "work_type": "status",
                "needs_live_access": False,
                "needs_code_changes": False,
                "needs_followup_workers": False,
            },
            "authority_used": ["worker-report.json"],
            "summary": "The report says the rebuild is green.",
            "findings": [
                {
                    "claim": "The rebuild is green.",
                    "basis": "Worker report summary.",
                    "confidence": "high",
                }
            ],
            "evidence": ["worker-report.json"],
            "unknowns": [],
            "recommended_next_action": "Continue with delegated worker reports.",
            "changed_files": [],
            "verification": ["report ingested"],
            "confidence": "high",
        }
        fake_worker = isolated / "fake_worker.py"
        fake_worker.write_text(
            "\n".join(
                [
                    "import json",
                    "import re",
                    "import sys",
                    "from pathlib import Path",
                    "prompt = sys.stdin.read()",
                    "match = re.search(r'(runs/amadeus-delegations/[^\\s]+/worker-report\\.json)', prompt)",
                    "if not match:",
                    "    raise SystemExit('report path not found in prompt')",
                    "report_path = Path(match.group(1))",
                    "report_path.parent.mkdir(parents=True, exist_ok=True)",
                    f"report = json.loads({json.dumps(json.dumps(report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "print('REPORT WRITTEN', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = isolated / "fake-profile.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": "fake-amadeus-worker",
                    "name": "Fake Amadeus Worker",
                    "description": "Fake worker profile for Amadeus session tests.",
                    "command": [sys.executable, "-S", str(fake_worker)],
                }
            ),
            encoding="utf-8",
        )
        run_result = run_delegation_job(
            isolated,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=15,
            idle_timeout_seconds=15,
            max_output_bytes=4096,
            force=True,
        )
        self.assertEqual(run_result["status"], "reported", json.dumps(run_result, indent=2, sort_keys=True))

        summary = start_executive_session(isolated, session_id="amadeus-exec", force=True)

        session_dir = isolated / "runs" / "amadeus-sessions" / "amadeus-exec"
        brief = (session_dir / "conversation-brief.md").read_text(encoding="utf-8")
        self.assertEqual(summary["status"], "fast_ready")
        self.assertEqual(summary["mode"], "amadeus-executive-start")
        self.assertIn("Amadeus executive mode is ready.", brief)
        self.assertIn("worker reports are the project authority", brief)
        self.assertIn("The report says the rebuild is green.", brief)
        self.assertIn("Amadeus to stay high-level", brief)
        self.assertFalse((isolated / "AGENTS.md").exists())

    def test_start_executive_session_does_not_inspect_git(self) -> None:
        from suite import amadeus_session
        from suite.contracts import validate_contract

        isolated = self.temp_dir / "isolated-executive-no-git"
        isolated.mkdir()

        with mock.patch.object(
            amadeus_session,
            "_git_snapshot",
            side_effect=AssertionError("git should not be inspected"),
        ):
            summary = amadeus_session.start_executive_session(
                isolated,
                session_id="amadeus-exec-no-git",
                force=True,
            )

        manifest_path = (
            isolated
            / "runs"
            / "amadeus-sessions"
            / "amadeus-exec-no-git"
            / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["mode"], "amadeus-executive-start")
        self.assertEqual(
            manifest["git_snapshot"],
            {
                "branch": None,
                "head": None,
                "status_lines": [],
                "recent_commits": [],
            },
        )
        self.assertEqual(validate_contract("amadeus-session", manifest), [])

    def test_refresh_session_rejects_executive_session_without_mutating_manifest(self) -> None:
        from suite.amadeus_session import AmadeusSessionError, refresh_session, start_executive_session

        start_executive_session(self.temp_dir, session_id="amadeus-exec-refresh", force=True)

        manifest_path = (
            self.temp_dir
            / "runs"
            / "amadeus-sessions"
            / "amadeus-exec-refresh"
            / "manifest.json"
        )
        before = json.loads(manifest_path.read_text(encoding="utf-8"))

        with self.assertRaisesRegex(
            AmadeusSessionError,
            "executive sessions refresh through `amadeus delegate create/run` "
            "or `amadeus executive-start --force`",
        ):
            refresh_session(self.temp_dir, session_id="amadeus-exec-refresh", deep=True)

        after = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(after, before)

    def test_start_session_reports_missing_handoff_without_hiding_it(self) -> None:
        from suite.amadeus_session import start_session

        (self.temp_dir / "docs" / "session-handoff.md").unlink()

        start_session(
            self.temp_dir,
            session_id="amadeus-missing-handoff",
            fast=True,
            background_deep=False,
            force=True,
        )

        fast_brief = json.loads(
            (
                self.temp_dir
                / "runs"
                / "amadeus-sessions"
                / "amadeus-missing-handoff"
                / "fast-brief.json"
            ).read_text(encoding="utf-8")
        )
        open_questions = (
            self.temp_dir
            / "runs"
            / "amadeus-sessions"
            / "amadeus-missing-handoff"
            / "open-questions.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(fast_brief["handoff"]["status"], "missing")
        self.assertIn("docs/session-handoff.md", fast_brief["uninspected_surfaces"])
        self.assertIn("docs/session-handoff.md", open_questions)

    def test_start_session_force_replaces_existing_session(self) -> None:
        from suite.amadeus_session import start_session

        start_session(self.temp_dir, session_id="amadeus-force", fast=True, force=True)
        marker = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-force" / "old.txt"
        marker.write_text("old", encoding="utf-8")

        start_session(self.temp_dir, session_id="amadeus-force", fast=True, force=True)

        self.assertFalse(marker.exists())

    def test_start_session_background_deep_without_wired_cli_stays_pending(self) -> None:
        from suite import amadeus_session

        with mock.patch.object(amadeus_session, "_amadeus_cli_available", return_value=False):
            summary = amadeus_session.start_session(
                self.temp_dir,
                session_id="amadeus-background-pending",
                fast=True,
                background_deep=True,
                force=True,
            )

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-background-pending"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "fast_ready")
        self.assertEqual(summary["deep_refresh_status"], "pending")
        self.assertEqual(manifest["status"], "fast_ready")
        self.assertEqual(manifest["deep_refresh"]["status"], "pending")
        self.assertEqual(manifest["deep_refresh"]["process_id"], None)
        self.assertEqual(manifest["deep_refresh"]["stdout_path"], None)
        self.assertEqual(manifest["deep_refresh"]["stderr_path"], None)
        self.assertEqual(manifest["deep_refresh"]["error"], "Amadeus refresh CLI is not available yet")
        self.assertFalse((session_dir / "background-deep.stdout.log").exists())

    def test_start_session_background_deep_records_running_process(self) -> None:
        from suite.amadeus_session import start_session

        calls = []

        def fake_launcher(command: list[str], stdout_path: Path, stderr_path: Path) -> dict:
            calls.append({"command": command, "stdout_path": stdout_path, "stderr_path": stderr_path})
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            return {"process_id": 12345}

        start_session(
            self.temp_dir,
            session_id="amadeus-background-custom",
            fast=True,
            background_deep=True,
            force=True,
            background_launcher=fake_launcher,
        )

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-background-custom"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(len(calls), 1)
        self.assertEqual(manifest["status"], "refresh_running")
        self.assertEqual(manifest["deep_refresh"]["status"], "running")
        self.assertEqual(manifest["deep_refresh"]["process_id"], 12345)
        self.assertTrue(manifest["deep_refresh"]["stdout_path"].endswith("background-deep.stdout.log"))
        self.assertTrue(manifest["deep_refresh"]["stderr_path"].endswith("background-deep.stderr.log"))

    def test_start_session_background_deep_does_not_overwrite_completed_refresh(self) -> None:
        from suite.amadeus_session import refresh_session, start_session

        self._write_loop_summary()

        def immediate_refresh(command: list[str], stdout_path: Path, stderr_path: Path) -> dict:
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            refresh_session(self.temp_dir, session_id="amadeus-background-race", deep=True)
            return {"process_id": 54321}

        summary = start_session(
            self.temp_dir,
            session_id="amadeus-background-race",
            fast=True,
            background_deep=True,
            force=True,
            background_launcher=immediate_refresh,
        )

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-background-race"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "refresh_complete")
        self.assertEqual(summary["deep_refresh_status"], "complete")
        self.assertEqual(manifest["status"], "refresh_complete")
        self.assertEqual(manifest["deep_refresh"]["status"], "complete")

    def test_start_session_background_deep_does_not_regress_late_completed_refresh(self) -> None:
        from suite import amadeus_session

        self._write_loop_summary()
        original_launch = amadeus_session._launch_background_refresh

        def fake_launcher(command: list[str], stdout_path: Path, stderr_path: Path) -> dict:
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            return {"process_id": 67890}

        def complete_after_launch_returns(**kwargs: object) -> dict:
            manifest = original_launch(**kwargs)
            amadeus_session.refresh_session(self.temp_dir, session_id="amadeus-background-late-race", deep=True)
            return manifest

        with mock.patch.object(
            amadeus_session,
            "_launch_background_refresh",
            side_effect=complete_after_launch_returns,
        ):
            summary = amadeus_session.start_session(
                self.temp_dir,
                session_id="amadeus-background-late-race",
                fast=True,
                background_deep=True,
                force=True,
                background_launcher=fake_launcher,
            )

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-background-late-race"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "refresh_complete")
        self.assertEqual(summary["deep_refresh_status"], "complete")
        self.assertEqual(manifest["status"], "refresh_complete")
        self.assertEqual(manifest["deep_refresh"]["status"], "complete")
        self.assertTrue((session_dir / "deep-refresh.json").exists())

    def test_start_session_background_launch_failure_leaves_usable_fast_session(self) -> None:
        from suite.amadeus_session import start_session

        def failing_launcher(command: list[str], stdout_path: Path, stderr_path: Path) -> dict:
            raise OSError("cannot launch")

        summary = start_session(
            self.temp_dir,
            session_id="amadeus-background-failure",
            fast=True,
            background_deep=True,
            force=True,
            background_launcher=failing_launcher,
        )

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-background-failure"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "fast_ready")
        self.assertEqual(summary["deep_refresh_status"], "pending")
        self.assertEqual(manifest["deep_refresh"]["status"], "pending")
        self.assertEqual(manifest["deep_refresh"]["error"], "cannot launch")
        self.assertTrue((session_dir / "conversation-brief.md").exists())

    def test_refresh_session_writes_deep_metrics_and_role_notes(self) -> None:
        from suite.amadeus_session import refresh_session, start_session

        self._write_loop_summary()
        start_session(self.temp_dir, session_id="amadeus-deep", fast=True, background_deep=False, force=True)

        summary = refresh_session(self.temp_dir, session_id="amadeus-deep", deep=True)

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-deep"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))
        deep_refresh = json.loads((session_dir / "deep-refresh.json").read_text(encoding="utf-8"))
        metrics = json.loads((session_dir / "metrics-summary.json").read_text(encoding="utf-8"))
        role_notes = (session_dir / "role-template-notes.jsonl").read_text(encoding="utf-8").splitlines()
        conversation = (session_dir / "conversation-brief.md").read_text(encoding="utf-8")

        self.assertEqual(summary["status"], "refresh_complete")
        self.assertEqual(manifest["status"], "refresh_complete")
        self.assertEqual(manifest["deep_refresh"]["status"], "complete")
        self.assertEqual(deep_refresh["latest_loop"]["status"], "present")
        self.assertEqual(metrics["pass_rate"], 1.0)
        self.assertEqual(metrics["runtime_hotspots"][0]["task_id"], "slow-task")
        self.assertGreaterEqual(len(role_notes), 5)
        self.assertIn("The deeper pull is in", conversation)

    def test_refresh_session_reports_missing_loop_without_failing(self) -> None:
        from suite.amadeus_session import refresh_session, start_session

        start_session(self.temp_dir, session_id="amadeus-missing-loop", fast=True, background_deep=False, force=True)

        summary = refresh_session(self.temp_dir, session_id="amadeus-missing-loop", deep=True)

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-missing-loop"
        deep_refresh = json.loads((session_dir / "deep-refresh.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "refresh_complete")
        self.assertEqual(deep_refresh["latest_loop"]["status"], "missing")
        self.assertIn("improvement-runs", deep_refresh["uninspected_surfaces"])

    def test_refresh_session_records_malformed_loop_without_stranding_manifest(self) -> None:
        from suite.amadeus_session import refresh_session, start_session

        self._write_malformed_completed_loop_summary()
        start_session(self.temp_dir, session_id="amadeus-bad-loop", fast=True, background_deep=False, force=True)

        summary = refresh_session(self.temp_dir, session_id="amadeus-bad-loop", deep=True)

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-bad-loop"
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))
        deep_refresh = json.loads((session_dir / "deep-refresh.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["status"], "refresh_complete")
        self.assertEqual(manifest["status"], "refresh_complete")
        self.assertEqual(manifest["deep_refresh"]["status"], "complete")
        self.assertEqual(deep_refresh["latest_loop"]["status"], "failed")
        self.assertIn("error", deep_refresh["latest_loop"])
        self.assertIn("summary_path", deep_refresh["latest_loop"])

    def test_refresh_session_preserves_background_debug_handles(self) -> None:
        from suite.amadeus_session import refresh_session, start_session

        start_session(self.temp_dir, session_id="amadeus-preserve-debug", fast=True, background_deep=False, force=True)
        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-preserve-debug"
        manifest_path = session_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["deep_refresh"]["process_id"] = 2468
        manifest["deep_refresh"]["stdout_path"] = "runs/amadeus-sessions/amadeus-preserve-debug/background-deep.stdout.log"
        manifest["deep_refresh"]["stderr_path"] = "runs/amadeus-sessions/amadeus-preserve-debug/background-deep.stderr.log"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        refresh_session(self.temp_dir, session_id="amadeus-preserve-debug", deep=True)

        completed = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(completed["deep_refresh"]["process_id"], 2468)
        self.assertEqual(
            completed["deep_refresh"]["stdout_path"],
            "runs/amadeus-sessions/amadeus-preserve-debug/background-deep.stdout.log",
        )
        self.assertEqual(
            completed["deep_refresh"]["stderr_path"],
            "runs/amadeus-sessions/amadeus-preserve-debug/background-deep.stderr.log",
        )

    def test_refresh_session_preserves_validation_token_and_tool_hotspots(self) -> None:
        from suite.amadeus_session import refresh_session, start_session

        self._write_validation_hotspot_loop_summary()
        start_session(self.temp_dir, session_id="amadeus-validation-hotspots", fast=True, background_deep=False, force=True)

        refresh_session(self.temp_dir, session_id="amadeus-validation-hotspots", deep=True)

        session_dir = self.temp_dir / "runs" / "amadeus-sessions" / "amadeus-validation-hotspots"
        metrics = json.loads((session_dir / "metrics-summary.json").read_text(encoding="utf-8"))

        self.assertEqual(
            metrics["validation_token_hotspots"][0]["task_id"],
            "token-tool-heavy-validation",
        )
        self.assertEqual(
            metrics["validation_tool_hotspots"][0]["task_id"],
            "token-tool-heavy-validation",
        )
        self.assertEqual(metrics["token_hotspots"][0]["task_id"], "token-heavy")
        self.assertEqual(metrics["tool_hotspots"][0]["task_id"], "tool-heavy")

    def test_render_brief_uses_deep_refresh_when_available(self) -> None:
        from suite.amadeus_session import refresh_session, render_brief, start_session

        self._write_loop_summary()
        start_session(self.temp_dir, session_id="amadeus-render-deep", fast=True, background_deep=False, force=True)
        refresh_session(self.temp_dir, session_id="amadeus-render-deep", deep=True)

        rendered = render_brief(self.temp_dir, session_id="amadeus-render-deep")

        self.assertIn("The deeper pull is in", rendered)
        self.assertIn("slow-task", rendered)

    def test_amadeus_cli_start_refresh_status_and_brief(self) -> None:
        self._write_loop_summary()

        start = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "start",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "amadeus-cli",
                "--fast",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertEqual(json.loads(start.stdout)["session_id"], "amadeus-cli")

        refresh = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "refresh",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "amadeus-cli",
                "--deep",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(refresh.returncode, 0, refresh.stderr)
        self.assertEqual(json.loads(refresh.stdout)["status"], "refresh_complete")

        status = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "status",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "amadeus-cli",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["deep_refresh"]["status"], "complete")

        brief = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "brief",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "amadeus-cli",
                "--format",
                "markdown",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(brief.returncode, 0, brief.stderr)
        self.assertIn("Amadeus is ready", brief.stdout)
        self.assertIn("The deeper pull is in", brief.stdout)

    def test_amadeus_executive_start_cli(self) -> None:
        isolated = self.temp_dir / "isolated-executive-cli"
        isolated.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "executive-start",
                "--repo-root",
                str(isolated),
                "--session-id",
                "amadeus-exec-cli",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "amadeus-executive-start")
        conversation = Path(payload["conversation_brief"]).read_text(encoding="utf-8")
        self.assertIn("Amadeus executive mode is ready.", conversation)

    def test_amadeus_cli_start_defaults_to_fast(self) -> None:
        start = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "start",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "amadeus-cli-default-fast",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertEqual(json.loads(start.stdout)["status"], "fast_ready")

    def test_amadeus_cli_refresh_defaults_to_deep(self) -> None:
        self._write_loop_summary()
        start = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "start",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "amadeus-cli-default-deep",
                "--fast",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(start.returncode, 0, start.stderr)

        refresh = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "refresh",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "amadeus-cli-default-deep",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(refresh.returncode, 0, refresh.stderr)
        self.assertEqual(json.loads(refresh.stdout)["status"], "refresh_complete")


class AmadeusManifestValidationOrderingTests(unittest.TestCase):
    """Manifest writes must validate BEFORE writing, not after.

    The old pattern (write_json then _validate_manifest from disk) leaves a
    malformed manifest persisted on disk before the validation error raises.
    """

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="amadeus-validation-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_invalid_manifest_update_does_not_persist_to_disk(self):
        from suite import amadeus_session
        from suite.artifacts import write_json
        from suite.contracts import ContractValidationError

        session_dir = self.temp_dir / "session"
        session_dir.mkdir()
        manifest_path = session_dir / "manifest.json"

        valid_initial = {
            "schema_version": "amadeus_session_v1",
            "session_id": "sess",
            "created_at": "2026-05-27T00:00:00Z",
            "updated_at": "2026-05-27T00:00:00Z",
            "repo_root": str(self.temp_dir),
            "status": "fast_ready",
            "git_snapshot": {
                "branch": None,
                "head": None,
                "status_lines": [],
                "recent_commits": [],
            },
            "fast_brief": {
                "status": "complete",
                "path": str(session_dir / "fast-brief.json"),
                "generated_at": None,
            },
            "deep_refresh": {
                "status": "not_started",
                "path": str(session_dir / "deep-refresh.json"),
                "command": "noop",
                "started_at": None,
                "completed_at": None,
                "process_id": None,
                "stdout_path": None,
                "stderr_path": None,
                "error": None,
            },
            "live_checks": {
                "network": False,
                "ssh": False,
                "browser": False,
                "api": False,
                "service_status": False,
            },
            "artifacts": [],
        }
        write_json(manifest_path, valid_initial)

        def break_it(manifest):
            broken = dict(manifest)
            broken.pop("schema_version", None)  # violate required field
            return broken

        with self.assertRaises(ContractValidationError):
            amadeus_session._update_manifest(manifest_path, break_it)

        # On-disk manifest must still be the valid initial state, not the broken update.
        on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(
            on_disk.get("schema_version"),
            "amadeus_session_v1",
            "broken update must not persist; on-disk state must match valid initial",
        )
