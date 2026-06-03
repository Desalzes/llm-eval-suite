import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


def _sample_report(job_id: str) -> dict:
    return {
        "schema_version": "amadeus_worker_report_v1",
        "job_id": job_id,
        "created_at": "2026-05-31T12:01:00Z",
        "role": "investigator",
        "request": "What is the state of the rebuild?",
        "scope_decision": {
            "work_type": "status",
            "needs_live_access": False,
            "needs_code_changes": False,
            "needs_followup_workers": False,
        },
        "authority_used": ["read_only"],
        "summary": "The rebuild is green.",
        "findings": [
            {
                "claim": "The rebuild is green.",
                "basis": "Focused unit tests passed.",
                "confidence": "high",
            }
        ],
        "evidence": ["tests/test_amadeus_delegation.py"],
        "unknowns": ["Live runtime was not inspected."],
        "recommended_next_action": "Proceed with the next delegation task.",
        "changed_files": [],
        "verification": ["python -m unittest discover -s tests -p test_amadeus_delegation.py -v"],
        "confidence": "high",
    }


class AmadeusDelegationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="amadeus-delegation-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_readme_documents_executive_delegation_commands(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        readme = (repo_root / "README.md").read_text(encoding="utf-8")

        self.assertIn("amadeus executive-start", readme)
        self.assertIn("amadeus delegate create", readme)
        self.assertIn("amadeus delegate run", readme)
        self.assertIn("worker reports are the project authority", readme)

        create_line = next(line for line in readme.splitlines() if "amadeus delegate create" in line)
        run_line = next(line for line in readme.splitlines() if "amadeus delegate run" in line)

        create_job_id = re.search(r"--job-id\s+(\S+)", create_line)
        run_job_id = re.search(r"--job-id\s+(\S+)", run_line)
        run_profile = re.search(r"--profile\s+(\S+)", run_line)

        self.assertIsNotNone(create_job_id)
        self.assertIsNotNone(run_job_id)
        self.assertEqual(create_job_id.group(1), run_job_id.group(1))
        self.assertIsNotNone(run_profile)
        self.assertEqual("profiles/codex-baseline.json", run_profile.group(1))
        self.assertTrue((repo_root / run_profile.group(1)).exists())

    def _write_profile(self, command: list[str]) -> Path:
        profile_path = self.temp_dir / "fake-agent-profile.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": "fake-amadeus-worker",
                    "name": "Fake Amadeus Worker",
                    "description": "Fake worker profile for Amadeus delegation tests.",
                    "command": command,
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def _skip_unless_file_symlinks_supported(self) -> None:
        target = self.temp_dir / "symlink-target.txt"
        link = self.temp_dir / "symlink-link.txt"
        target.write_text("target", encoding="utf-8")
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"file symlinks are not available in this environment: {exc}")
        finally:
            if link.is_symlink() or link.exists():
                link.unlink()
            if target.exists():
                target.unlink()

    def _mark_job_running_for_ingest(self, created: dict, job_id: str) -> None:
        return None

    def _run_worker_with_current_report(self, repo_root: Path, job_id: str) -> dict:
        from suite.amadeus_delegation import run_delegation_job

        report_path = repo_root / "runs" / "amadeus-delegations" / job_id / "worker-report.json"
        report_text = report_path.read_text(encoding="utf-8")
        report_path.unlink()
        fake_worker = self.temp_dir / f"fake_ingest_{job_id}.py"
        fake_worker.write_text(
            "\n".join(
                [
                    "import re",
                    "import sys",
                    "from pathlib import Path",
                    "prompt = sys.stdin.read()",
                    "match = re.search(r'(runs/amadeus-delegations/[^\\s]+/worker-report\\.json)', prompt)",
                    "if not match:",
                    "    raise SystemExit('report path not found in prompt')",
                    "report_path = Path(match.group(1))",
                    "report_path.parent.mkdir(parents=True, exist_ok=True)",
                    f"report_text = {report_text!r}",
                    "report_path.write_text(report_text, encoding='utf-8')",
                    "print('REPORT WRITTEN', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])
        return run_delegation_job(
            repo_root,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=15,
            idle_timeout_seconds=15,
            max_output_bytes=4096,
            force=True,
        )

    def _ingest_worker_report(self, repo_root: Path, job_id: str) -> dict:
        result = self._run_worker_with_current_report(repo_root, job_id)
        self.assertEqual(result["status"], "reported", json.dumps(result, indent=2, sort_keys=True))
        return result

    def test_create_delegation_job_writes_contract_and_prompts_without_project_reads(self) -> None:
        from suite.amadeus_delegation import create_delegation_job

        result = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            project_hint="ChatGPT",
            authority="read_only",
            requested_output="status_report",
            session_id="amadeus-unit",
            job_id="amadeus-job-20260531-120000",
            force=True,
        )

        job_dir = Path(result["job_dir"])
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        scoper_prompt = (job_dir / "scoper-prompt.md").read_text(encoding="utf-8")
        worker_prompt = (job_dir / "worker-prompt.md").read_text(encoding="utf-8")

        self.assertEqual(job["schema_version"], "amadeus_delegation_job_v1")
        self.assertEqual(job["status"], "created")
        self.assertEqual(job["user_request"], "What is the state of the rebuild?")
        self.assertEqual(job["authority"], "read_only")
        self.assertIn("You are the Amadeus scoper worker.", scoper_prompt)
        self.assertIn("You decide the scope", scoper_prompt)
        self.assertIn("You are an Amadeus worker.", worker_prompt)
        self.assertIn("worker-report.json", worker_prompt)
        self.assertFalse((self.temp_dir / "AGENTS.md").exists(), "test repo intentionally has no project docs")

    def test_create_delegation_rejects_empty_request(self) -> None:
        from suite.amadeus_delegation import create_delegation_job

        with self.assertRaises(ValueError):
            create_delegation_job(
                self.temp_dir,
                user_request="   ",
                job_id="amadeus-job-20260531-120001",
                force=True,
            )

    def test_create_delegation_rejects_invalid_job_id_without_partial_artifacts(self) -> None:
        from suite.amadeus_delegation import create_delegation_job
        from suite.contracts import ContractValidationError

        with self.assertRaises(ContractValidationError):
            create_delegation_job(
                self.temp_dir,
                user_request="What is the state of the rebuild?",
                job_id="invalid-job-id",
                force=True,
            )

        self.assertFalse((self.temp_dir / "runs" / "amadeus-delegations" / "invalid-job-id").exists())

    def test_default_delegation_jobs_get_distinct_valid_ids_and_directories(self) -> None:
        from suite.amadeus_delegation import create_delegation_job

        class FrozenDatetime:
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 5, 31, 12, 0, 2, tzinfo=timezone.utc)

        with patch("suite.amadeus_delegation.datetime", FrozenDatetime):
            first = create_delegation_job(self.temp_dir, user_request="Assess rebuild status.")
            second = create_delegation_job(self.temp_dir, user_request="Assess rebuild status.")

        self.assertNotEqual(first["job_id"], second["job_id"])
        self.assertRegex(first["job_id"], r"^amadeus-job-[0-9]{8}-[0-9]{6}-[a-z0-9-]+$")
        self.assertRegex(second["job_id"], r"^amadeus-job-[0-9]{8}-[0-9]{6}-[a-z0-9-]+$")
        self.assertTrue(Path(first["job_dir"]).is_dir())
        self.assertTrue(Path(second["job_dir"]).is_dir())
        self.assertNotEqual(Path(first["job_dir"]), Path(second["job_dir"]))

    def test_ingest_worker_report_validates_and_marks_job_reported(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120100"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

        result = self._ingest_worker_report(self.temp_dir, job_id)

        job_dir = Path(created["job_dir"])
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        markdown = (job_dir / "worker-report.md").read_text(encoding="utf-8")
        self.assertEqual(result["status"], "reported")
        self.assertEqual(job["status"], "reported")
        self.assertIn("worker-report.md", job["artifacts"])
        self.assertIn("The rebuild is green", markdown)

    def test_ingest_worker_report_rejects_disk_only_worker_run_evidence(self) -> None:
        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120106"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")
        job_dir = Path(created["job_dir"])
        job_path = job_dir / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["status"] = "running"
        job["worker"]["backend"] = "command"
        job["worker"]["profile_path"] = "fake-agent-profile.json"
        job["worker"]["agent_session_dir"] = f"runs/amadeus-delegations/{job_id}/agent-runs/{job_id}-worker"
        job["worker"]["allowed_paths"] = [f"runs/amadeus-delegations/{job_id}/*"]
        job["worker"]["run_evidence"] = {
            "session_id": f"{job_id}-worker",
            "session_dir": job["worker"]["agent_session_dir"],
            "session_type": "suite-agent-session",
            "contract_version": 1,
            "backend": "command",
            "status": "passed",
            "prompt_sha256": "0" * 64,
            "profile_command_sha256": "1" * 64,
            "manifest_sha256": "2" * 64,
            "result_sha256": "3" * 64,
        }
        job["artifacts"] = list(dict.fromkeys([*job["artifacts"], "agent-runs"]))
        job_path.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(AmadeusDelegationError, "only be ingested by run_delegation_job"):
            ingest_worker_report(self.temp_dir, job_id=job_id)

        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "running")
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_worker_report_rejects_created_job_without_partial_update(self) -> None:
        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120101"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

        with self.assertRaisesRegex(AmadeusDelegationError, "created delegation jobs cannot be ingested"):
            ingest_worker_report(self.temp_dir, job_id=job_id)

        job_dir = Path(created["job_dir"])
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "created")
        self.assertNotIn("worker-report.md", job["artifacts"])
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_worker_report_rejects_running_job_without_worker_run_evidence(self) -> None:
        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        cases = [
            ("amadeus-job-20260531-120103", None, True),
            ("amadeus-job-20260531-120104", "agent_session_dir", False),
        ]
        for job_id, session_marker, include_agent_runs in cases:
            with self.subTest(job_id=job_id):
                created = create_delegation_job(
                    self.temp_dir,
                    user_request="What is the state of the rebuild?",
                    job_id=job_id,
                    force=True,
                )
                job_dir = Path(created["job_dir"])
                job_path = job_dir / "job.json"
                job = json.loads(job_path.read_text(encoding="utf-8"))
                job["status"] = "running"
                if session_marker is not None:
                    session_dir = job_dir / "agent-runs" / f"{job_id}-worker"
                    session_dir.mkdir(parents=True)
                    (session_dir / "result.json").write_text(
                        json.dumps({"run_id": f"{job_id}-worker", "status": "passed"}, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    job["worker"]["agent_session_dir"] = session_dir.relative_to(self.temp_dir).as_posix()
                if include_agent_runs:
                    job["artifacts"] = list(dict.fromkeys([*job["artifacts"], "agent-runs"]))
                job_path.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

                with self.assertRaisesRegex(AmadeusDelegationError, "only be ingested by run_delegation_job"):
                    ingest_worker_report(self.temp_dir, job_id=job_id)

                persisted_job = json.loads(job_path.read_text(encoding="utf-8"))
                self.assertEqual(persisted_job["status"], "running")
                self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_worker_report_rejects_unpassed_disk_session_result(self) -> None:
        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120105"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        job_dir = Path(created["job_dir"])
        job_path = job_dir / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["status"] = "running"
        job["worker"]["backend"] = "command"
        job["worker"]["profile_path"] = "fake-agent-profile.json"
        job["worker"]["agent_session_dir"] = f"runs/amadeus-delegations/{job_id}/agent-runs/{job_id}-worker"
        job["worker"]["allowed_paths"] = [f"runs/amadeus-delegations/{job_id}/*"]
        job["worker"]["run_evidence"] = {
            "session_id": f"{job_id}-worker",
            "session_dir": job["worker"]["agent_session_dir"],
            "session_type": "suite-agent-session",
            "contract_version": 1,
            "backend": "command",
            "status": "failed",
            "prompt_sha256": "0" * 64,
            "profile_command_sha256": "1" * 64,
            "manifest_sha256": "2" * 64,
            "result_sha256": "3" * 64,
        }
        job["artifacts"] = list(dict.fromkeys([*job["artifacts"], "agent-runs"]))
        job_path.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

        with self.assertRaisesRegex(AmadeusDelegationError, "only be ingested by run_delegation_job"):
            ingest_worker_report(self.temp_dir, job_id=job_id)

        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "running")
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_worker_report_rejects_reported_job_without_rewriting_markdown(self) -> None:
        from suite.amadeus_delegation import (
            AmadeusDelegationError,
            create_delegation_job,
            ingest_worker_report,
            list_worker_reports,
        )

        job_id = "amadeus-job-20260531-120102"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")
        self._ingest_worker_report(self.temp_dir, job_id)

        job_dir = Path(created["job_dir"])
        markdown_path = job_dir / "worker-report.md"
        original_markdown = markdown_path.read_text(encoding="utf-8")
        mutated_report = _sample_report(job_id)
        mutated_report["summary"] = "This mutation must not be promoted."
        Path(created["report"]).write_text(json.dumps(mutated_report), encoding="utf-8")

        with self.assertRaisesRegex(AmadeusDelegationError, "reported delegation jobs cannot be ingested again"):
            ingest_worker_report(self.temp_dir, job_id=job_id)

        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "reported")
        self.assertEqual(markdown_path.read_text(encoding="utf-8"), original_markdown)
        self.assertNotIn("This mutation must not be promoted.", original_markdown)
        self.assertEqual(list_worker_reports(self.temp_dir, limit=5), [])

    def test_list_reports_and_render_index(self) -> None:
        from suite.amadeus_delegation import (
            create_delegation_job,
            ingest_worker_report,
            list_worker_reports,
            render_report_index,
        )

        job_id = "amadeus-job-20260531-120200"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")
        self._ingest_worker_report(self.temp_dir, job_id)

        reports = list_worker_reports(self.temp_dir, limit=5)
        markdown = render_report_index(reports)

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["job_id"], job_id)
        self.assertIn("The rebuild is green", markdown)
        self.assertIn(job_id, markdown)

    def test_amadeus_delegate_create_and_report_cli(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        job_id = "amadeus-job-20260531-120400"

        create_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "create",
                "--repo-root",
                str(self.temp_dir),
                "--job-id",
                job_id,
                "--request",
                "What is the state of the rebuild?",
                "--project-hint",
                "ChatGPT",
                "--authority",
                "read_only",
                "--requested-output",
                "status_report",
                "--force",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(create_result.returncode, 0, create_result.stderr + create_result.stdout)
        json.loads(create_result.stdout)

        fake_worker = self.temp_dir / "fake_cli_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(_sample_report(job_id)))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "print('REPORT WRITTEN', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        run_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "run",
                "--repo-root",
                str(self.temp_dir),
                "--job-id",
                job_id,
                "--profile",
                str(profile_path),
                "--timeout-seconds",
                "5",
                "--idle-timeout-seconds",
                "5",
                "--max-output-bytes",
                "4096",
                "--force",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(run_result.returncode, 0, run_result.stderr + run_result.stdout)
        self.assertIn("worker-report.md", run_result.stdout)

        report_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "report",
                "--repo-root",
                str(self.temp_dir),
                "--job-id",
                job_id,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(report_result.returncode, 0, report_result.stderr + report_result.stdout)
        self.assertIn("The rebuild is green", report_result.stdout)

        list_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "list",
                "--repo-root",
                str(self.temp_dir),
                "--format",
                "markdown",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(list_result.returncode, 0, list_result.stderr + list_result.stdout)
        self.assertIn("# Amadeus Worker Reports", list_result.stdout)
        self.assertIn(job_id, list_result.stdout)
        self.assertIn("The rebuild is green", list_result.stdout)

    def test_amadeus_delegate_report_rejects_absolute_job_id_without_printing_external_markdown(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        outside_dir = Path(tempfile.mkdtemp(prefix="amadeus-external-report-"))
        sentinel = "SENTINEL OUTSIDE AMADEUS REPORT"

        try:
            (outside_dir / "worker-report.md").write_text(sentinel, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "suite.cli",
                    "amadeus",
                    "delegate",
                    "report",
                    "--repo-root",
                    str(self.temp_dir),
                    "--job-id",
                    str(outside_dir.resolve()),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(sentinel, result.stdout)
        self.assertNotIn(sentinel, result.stderr)

    def test_amadeus_delegate_report_rejects_corrupt_current_report_without_printing_stale_markdown(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, ingest_worker_report

        repo_root = Path(__file__).resolve().parents[1]
        job_id = "amadeus-job-20260531-120410"
        corrupt_job_id = "amadeus-job-20260531-120411"
        stale_summary = "The rebuild is green."

        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")
        self._ingest_worker_report(self.temp_dir, job_id)

        corrupt_report = _sample_report(corrupt_job_id)
        corrupt_report["summary"] = "This corrupt report must not be rendered."
        Path(created["report"]).write_text(json.dumps(corrupt_report), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "report",
                "--repo-root",
                str(self.temp_dir),
                "--job-id",
                job_id,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(stale_summary, result.stdout)
        self.assertNotIn(stale_summary, result.stderr)

    def test_amadeus_delegate_report_rejects_mutated_current_report_without_printing_mutation(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, ingest_worker_report

        repo_root = Path(__file__).resolve().parents[1]
        job_id = "amadeus-job-20260531-120413"
        mutated_summary = "This same-job mutation must not be rendered."

        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")
        self._ingest_worker_report(self.temp_dir, job_id)

        mutated_report = _sample_report(job_id)
        mutated_report["summary"] = mutated_summary
        mutated_report["findings"][0]["claim"] = mutated_summary
        Path(created["report"]).write_text(json.dumps(mutated_report), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "report",
                "--repo-root",
                str(self.temp_dir),
                "--job-id",
                job_id,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(mutated_summary, result.stdout)
        self.assertNotIn(mutated_summary, result.stderr)

    def test_amadeus_delegate_report_rejects_symlinked_current_report_without_printing_target(self) -> None:
        self._skip_unless_file_symlinks_supported()

        from suite.amadeus_delegation import create_delegation_job, ingest_worker_report

        repo_root = Path(__file__).resolve().parents[1]
        job_id = "amadeus-job-20260531-120412"
        symlink_summary = "This symlink target report must not be rendered."

        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")
        self._ingest_worker_report(self.temp_dir, job_id)

        symlink_target = self.temp_dir / "local" / "conversation-memory" / "turns.jsonl"
        symlink_target.parent.mkdir(parents=True)
        target_report = _sample_report(job_id)
        target_report["summary"] = symlink_summary
        symlink_target.write_text(json.dumps(target_report), encoding="utf-8")

        report_path = Path(created["report"])
        report_path.unlink()
        report_path.symlink_to(symlink_target)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "report",
                "--repo-root",
                str(self.temp_dir),
                "--job-id",
                job_id,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(symlink_summary, result.stdout)
        self.assertNotIn(symlink_summary, result.stderr)

    def test_list_reports_skips_mismatched_report_identity(self) -> None:
        from suite.amadeus_delegation import (
            create_delegation_job,
            ingest_worker_report,
            list_worker_reports,
            render_report_index,
        )

        valid_job_id = "amadeus-job-20260531-120250"
        valid_created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=valid_job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(valid_created, valid_job_id)
        Path(valid_created["report"]).write_text(json.dumps(_sample_report(valid_job_id)), encoding="utf-8")
        self._ingest_worker_report(self.temp_dir, valid_job_id)

        mismatched_dir_id = "amadeus-job-20260531-120251"
        mismatched_report_id = "amadeus-job-20260531-120252"
        mismatched_created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=mismatched_dir_id,
            force=True,
        )
        self._mark_job_running_for_ingest(mismatched_created, mismatched_dir_id)
        Path(mismatched_created["report"]).write_text(json.dumps(_sample_report(mismatched_dir_id)), encoding="utf-8")
        self._ingest_worker_report(self.temp_dir, mismatched_dir_id)

        mismatched_report = _sample_report(mismatched_report_id)
        mismatched_report["summary"] = "This mismatched report must not be indexed."
        Path(mismatched_created["report"]).write_text(json.dumps(mismatched_report), encoding="utf-8")

        reports = list_worker_reports(self.temp_dir, limit=5)
        markdown = render_report_index(reports)

        self.assertEqual([report["job_id"] for report in reports], [valid_job_id])
        self.assertNotIn(mismatched_report_id, markdown)
        self.assertNotIn("This mismatched report must not be indexed.", markdown)

    def test_list_reports_skips_unreported_job_reports(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, list_worker_reports

        job_id = "amadeus-job-20260531-120260"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

        reports = list_worker_reports(self.temp_dir, limit=5)

        self.assertEqual(reports, [])

    def test_authoritative_report_readers_reject_disk_forged_reported_job(self) -> None:
        from suite.amadeus_delegation import (
            AmadeusDelegationError,
            create_delegation_job,
            list_worker_reports,
            load_authoritative_worker_report,
            render_report_index,
        )

        repo_root = Path(__file__).resolve().parents[1]
        job_id = "amadeus-job-20260531-120261"
        forged_summary = "This forged reported job must not be trusted."
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        report = _sample_report(job_id)
        report["summary"] = forged_summary
        report["findings"][0]["claim"] = forged_summary
        report_path = Path(created["report"])
        report_path.write_text(json.dumps(report), encoding="utf-8")

        job_path = Path(created["job"])
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["status"] = "reported"
        job["worker_report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
        job["artifacts"] = list(dict.fromkeys([*job["artifacts"], "worker-report.json", "worker-report.md"]))
        job_path.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        reports = list_worker_reports(self.temp_dir, limit=5)
        markdown = render_report_index(reports)

        self.assertEqual(reports, [])
        self.assertNotIn(forged_summary, markdown)
        with self.assertRaisesRegex(AmadeusDelegationError, "not authoritative"):
            load_authoritative_worker_report(self.temp_dir, job_id=job_id)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "amadeus",
                "delegate",
                "report",
                "--repo-root",
                str(self.temp_dir),
                "--job-id",
                job_id,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(forged_summary, result.stdout)
        self.assertNotIn(forged_summary, result.stderr)

    def test_run_delegation_job_uses_agent_session_and_ingests_report(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120300"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "Fake worker completed."
        fake_report["findings"][0]["claim"] = "Fake worker completed."
        fake_report["findings"][0]["basis"] = "The fake worker wrote the report."
        fake_worker = self.temp_dir / "fake_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "print('REPORT WRITTEN', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        markdown = (job_dir / "worker-report.md").read_text(encoding="utf-8")
        self.assertEqual(result["status"], "reported")
        self.assertEqual(result["agent_session"]["status"], "passed")
        self.assertEqual(job["worker"]["backend"], "command")
        self.assertIsNotNone(job["worker"]["agent_session_dir"])
        self.assertIn("agent-runs", job["artifacts"])
        self.assertIn("worker-report.json", job["artifacts"])
        self.assertIn("Fake worker completed.", markdown)

    def test_run_delegation_job_marks_failed_when_agent_session_fails(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120310"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        failing_worker = self.temp_dir / "failing_worker.py"
        failing_worker.write_text(
            "import sys\nprint('NO REPORT', flush=True)\nsys.exit(1)\n",
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(failing_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["agent_session"]["status"], "failed")
        self.assertEqual(job["status"], "failed")
        self.assertIsNotNone(job["worker"]["agent_session_dir"])
        self.assertIn("agent-runs", job["artifacts"])
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_run_delegation_job_marks_failed_when_agent_session_raises(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120320"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=self.temp_dir / "missing-profile.json",
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "FileNotFoundError")
        self.assertIn("missing-profile.json", result["error"])
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(job["worker"]["agent_session_dir"])
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_run_delegation_job_fails_unauthorized_delegation_writes_before_ingest(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120330"
        other_job_id = "amadeus-job-20260531-120331"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=other_job_id,
            force=True,
        )
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "Fake worker completed with an unsafe side effect."
        fake_worker = self.temp_dir / "unsafe_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    (
                        "unauthorized_path = "
                        f"Path('runs/amadeus-delegations/{other_job_id}/unauthorized.txt')"
                    ),
                    "unauthorized_path.write_text('not allowed', encoding='utf-8')",
                    "print('REPORT WRITTEN UNSAFELY', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        unauthorized = f"runs/amadeus-delegations/{other_job_id}/unauthorized.txt"
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "UnauthorizedDelegationChanges")
        self.assertIn(unauthorized, result["unauthorized_changes"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())
        self.assertNotIn("worker-report.md", job["artifacts"])

    def test_run_delegation_job_fails_unauthorized_delegation_directory_before_ingest(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120332"
        other_job_id = "amadeus-job-20260531-120333"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=other_job_id,
            force=True,
        )
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "Fake worker completed with an unsafe directory side effect."
        fake_worker = self.temp_dir / "unsafe_directory_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    (
                        "unauthorized_dir = "
                        f"Path('runs/amadeus-delegations/{other_job_id}/agent-runs/{other_job_id}-worker')"
                    ),
                    "unauthorized_dir.mkdir(parents=True, exist_ok=True)",
                    "print('REPORT WRITTEN WITH UNSAFE DIRECTORY', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        unauthorized = f"runs/amadeus-delegations/{other_job_id}/agent-runs"
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "UnauthorizedDelegationChanges")
        self.assertIn(unauthorized, result["unauthorized_changes"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())
        self.assertNotIn("worker-report.md", job["artifacts"])

    def test_run_delegation_job_fails_unauthorized_non_delegation_runs_write_before_ingest(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120334"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "Fake worker completed with an unsafe runs side effect."
        fake_worker = self.temp_dir / "unsafe_runs_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "unauthorized_path = Path('runs/amadeus-sessions/unauthorized-session/marker.txt')",
                    "unauthorized_path.parent.mkdir(parents=True, exist_ok=True)",
                    "unauthorized_path.write_text('not allowed', encoding='utf-8')",
                    "print('REPORT WRITTEN WITH UNSAFE RUNS WRITE', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        unauthorized = "runs/amadeus-sessions/unauthorized-session/marker.txt"
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "UnauthorizedDelegationChanges")
        self.assertIn(unauthorized, result["unauthorized_changes"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())
        self.assertNotIn("worker-report.md", job["artifacts"])

    def test_run_delegation_job_fails_unauthorized_local_write_before_ingest(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120335"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "Fake worker completed with an unsafe local side effect."
        fake_worker = self.temp_dir / "unsafe_local_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "unauthorized_path = Path('local/conversation-memory/turns.jsonl')",
                    "unauthorized_path.parent.mkdir(parents=True, exist_ok=True)",
                    "unauthorized_path.write_text('{\"role\":\"worker\",\"content\":\"forged\"}\\n', encoding='utf-8')",
                    "print('REPORT WRITTEN WITH UNSAFE LOCAL WRITE', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        unauthorized = "local/conversation-memory/turns.jsonl"
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "UnauthorizedDelegationChanges")
        self.assertIn(unauthorized, result["unauthorized_changes"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())
        self.assertNotIn("worker-report.md", job["artifacts"])

    def test_run_delegation_job_fails_unauthorized_ignored_root_write_before_ingest(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120336"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "Fake worker completed with an unsafe ignored-root side effect."
        fake_worker = self.temp_dir / "unsafe_ignored_root_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "unauthorized_path = Path('references/unauthorized-marker.txt')",
                    "unauthorized_path.parent.mkdir(parents=True, exist_ok=True)",
                    "unauthorized_path.write_text('not allowed', encoding='utf-8')",
                    "print('REPORT WRITTEN WITH UNSAFE IGNORED-ROOT WRITE', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        unauthorized = "references/unauthorized-marker.txt"
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "UnauthorizedDelegationChanges")
        self.assertIn(unauthorized, result["unauthorized_changes"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())
        self.assertNotIn("worker-report.md", job["artifacts"])

    def test_run_delegation_job_allows_pi_session_transcript_for_pi_backend(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120337"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "Fake Pi worker completed."
        pi_rows = [
            {
                "type": "session",
                "id": "pi-session-amadeus",
                "timestamp": "2026-05-31T12:03:00.000Z",
                "cwd": str(self.temp_dir),
            },
            {"type": "model_change", "provider": "google", "modelId": "gemini-2.5-flash-lite"},
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "provider": "google",
                    "model": "gemini-2.5-flash-lite",
                    "stopReason": "stop",
                    "usage": {"totalTokens": 13, "cost": {"total": 0.0013}},
                    "content": [{"type": "text", "text": "Pi worker complete."}],
                },
            },
        ]
        fake_worker = self.temp_dir / "fake_pi_worker.py"
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
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "pi_dir = Path('local/pi-sessions')",
                    "pi_dir.mkdir(parents=True, exist_ok=True)",
                    f"rows = json.loads({json.dumps(json.dumps(pi_rows))})",
                    "target = pi_dir / 'pi-session-amadeus.jsonl'",
                    "target.write_text(''.join(json.dumps(row) + '\\n' for row in rows), encoding='utf-8')",
                    "print('REPORT AND PI SESSION WRITTEN', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="pi",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "reported")
        self.assertEqual(job["status"], "reported")
        self.assertEqual(result["agent_session"]["status"], "passed")
        self.assertIsNotNone(result["agent_session"]["pi_session"])
        self.assertEqual(result["agent_session"]["pi_session"]["status"], "passed")
        self.assertEqual(result["agent_session"]["pi_session"]["session_id"], "pi-session-amadeus")
        self.assertTrue((job_dir / "worker-report.md").exists())

    def test_run_delegation_job_marks_failed_when_report_ingest_fails(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120340"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        fake_worker = self.temp_dir / "missing_report_worker.py"
        fake_worker.write_text(
            "print('NO REPORT WRITTEN', flush=True)\n",
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "AmadeusDelegationError")
        self.assertIn("worker report does not exist", result["error"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_run_delegation_job_rejects_stale_report_after_previous_failed_run(self) -> None:
        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120350"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        stale_report = _sample_report(job_id)
        stale_report["summary"] = "This stale report must not be ingested."
        failing_writer = self.temp_dir / "failing_report_writer.py"
        failing_writer.write_text(
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
                    f"report = json.loads({json.dumps(json.dumps(stale_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "print('STALE REPORT WRITTEN BEFORE FAILURE', flush=True)",
                    "sys.exit(1)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(failing_writer)])

        first_result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        self.assertEqual(first_result["status"], "failed")
        self.assertTrue((job_dir / "worker-report.json").exists())
        self.assertFalse((job_dir / "worker-report.md").exists())

        noop_worker = self.temp_dir / "noop_worker.py"
        noop_worker.write_text(
            "print('NOOP PASS WITHOUT REPORT', flush=True)\n",
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(noop_worker)])

        second_result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(second_result["status"], "failed")
        self.assertEqual(second_result["error_type"], "StaleWorkerReport")
        self.assertIn("worker report was not produced or changed", second_result["error"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_run_delegation_job_rejects_symlinked_report_before_ingest(self) -> None:
        self._skip_unless_file_symlinks_supported()

        from suite.amadeus_delegation import create_delegation_job, run_delegation_job

        job_id = "amadeus-job-20260531-120370"
        create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        protected_target = self.temp_dir / "local" / "conversation-memory" / "turns.jsonl"
        protected_target.parent.mkdir(parents=True)
        protected_target.write_text("stale conversation memory", encoding="utf-8")
        fake_report = _sample_report(job_id)
        fake_report["summary"] = "This symlinked report must not be ingested."
        fake_worker = self.temp_dir / "symlinked_report_worker.py"
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
                    "protected_path = Path('local/conversation-memory/turns.jsonl')",
                    "if report_path.exists() or report_path.is_symlink():",
                    "    report_path.unlink()",
                    "report_path.symlink_to(protected_path.resolve())",
                    f"report = json.loads({json.dumps(json.dumps(fake_report))})",
                    "report_path.write_text(json.dumps(report), encoding='utf-8')",
                    "print('SYMLINKED REPORT WRITTEN', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        profile_path = self._write_profile([sys.executable, "-S", str(fake_worker)])

        result = run_delegation_job(
            self.temp_dir,
            job_id=job_id,
            profile_path=profile_path,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        job_dir = self.temp_dir / "runs" / "amadeus-delegations" / job_id
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "UnauthorizedDelegationChanges")
        self.assertIn("local/conversation-memory/turns.jsonl", result["unauthorized_changes"])
        self.assertIn(f"runs/amadeus-delegations/{job_id}/worker-report.json", result["unauthorized_changes"])
        self.assertEqual(job["status"], "failed")
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_invalid_worker_report_does_not_update_job_or_markdown(self) -> None:
        from suite.amadeus_delegation import create_delegation_job

        job_id = "amadeus-job-20260531-120300"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        invalid_report = _sample_report(job_id)
        invalid_report.pop("summary")
        Path(created["report"]).write_text(json.dumps(invalid_report), encoding="utf-8")

        result = self._run_worker_with_current_report(self.temp_dir, job_id)

        job_dir = Path(created["job_dir"])
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "ContractValidationError")
        self.assertEqual(job["status"], "failed")
        self.assertNotIn("worker-report.md", job["artifacts"])
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_rejects_failed_job_without_partial_update(self) -> None:
        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120360"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        job_dir = Path(created["job_dir"])
        job_path = job_dir / "job.json"
        failed_job = json.loads(job_path.read_text(encoding="utf-8"))
        failed_job["status"] = "failed"
        job_path.write_text(json.dumps(failed_job, indent=2) + "\n", encoding="utf-8")
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

        with self.assertRaises(AmadeusDelegationError):
            ingest_worker_report(self.temp_dir, job_id=job_id)

        persisted_job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted_job["status"], "failed")
        self.assertNotIn("worker-report.md", persisted_job["artifacts"])
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_rejects_symlinked_worker_report_without_partial_update(self) -> None:
        self._skip_unless_file_symlinks_supported()

        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120361"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        job_dir = Path(created["job_dir"])
        job_path = job_dir / "job.json"
        protected_target = self.temp_dir / "local" / "conversation-memory" / "turns.jsonl"
        protected_target.parent.mkdir(parents=True)
        protected_target.write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")
        Path(created["report"]).symlink_to(protected_target)

        with self.assertRaises(AmadeusDelegationError):
            ingest_worker_report(self.temp_dir, job_id=job_id)

        persisted_job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted_job["status"], "created")
        self.assertNotIn("worker-report.md", persisted_job["artifacts"])
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_rejects_report_path_outside_job_directory_without_partial_update(self) -> None:
        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120400"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        job_dir = Path(created["job_dir"])
        job_path = job_dir / "job.json"

        with tempfile.TemporaryDirectory(prefix="amadeus-outside-report-") as outside_dir:
            outside_report = Path(outside_dir) / "worker-report.json"
            outside_report.write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

            job = json.loads(job_path.read_text(encoding="utf-8"))
            job["worker"]["report_path"] = str(outside_report.resolve())
            job_path.write_text(json.dumps(job), encoding="utf-8")

            with self.assertRaises(AmadeusDelegationError):
                ingest_worker_report(self.temp_dir, job_id=job_id)

        persisted_job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted_job["status"], "created")
        self.assertNotIn("worker-report.md", persisted_job["artifacts"])
        self.assertFalse((job_dir / "worker-report.md").exists())

    def test_ingest_rejects_mismatched_job_json_identity_without_partial_update(self) -> None:
        from suite.amadeus_delegation import AmadeusDelegationError, create_delegation_job, ingest_worker_report

        job_id = "amadeus-job-20260531-120400"
        created = create_delegation_job(
            self.temp_dir,
            user_request="What is the state of the rebuild?",
            job_id=job_id,
            force=True,
        )
        self._mark_job_running_for_ingest(created, job_id)
        job_dir = Path(created["job_dir"])
        job_path = job_dir / "job.json"

        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["job_id"] = "amadeus-job-20260531-120401"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        Path(created["report"]).write_text(json.dumps(_sample_report(job_id)), encoding="utf-8")

        with self.assertRaises(AmadeusDelegationError):
            ingest_worker_report(self.temp_dir, job_id=job_id)

        persisted_job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted_job["status"], "created")
        self.assertFalse((job_dir / "worker-report.md").exists())


if __name__ == "__main__":
    unittest.main()
