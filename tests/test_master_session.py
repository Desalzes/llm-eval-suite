import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class MasterSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="master-session-test-"))
        self._write_required_files(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_required_files(self, root: Path) -> None:
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
        (root / "README.md").write_text("# Project\n", encoding="utf-8")
        (root / "docs" / "session-handoff.md").write_text("# Handoff\n", encoding="utf-8")
        (root / "docs" / "agent-orchestration-roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
        (root / "docs" / "workflow-stack.md").write_text("# Workflow\n", encoding="utf-8")
        (root / "docs" / "master-session-contract.md").write_text("# Contract\n", encoding="utf-8")

    def _write_project_pack_registry(self, scope: str, pack_path: str) -> None:
        registry_dir = self.temp_dir / "configs" / "project-packs"
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry = {
            "schema_version": "project_pack_registry_v1",
            "packs": {
                scope.upper(): {
                    "path": pack_path,
                }
            },
        }
        (registry_dir / "index.json").write_text(json.dumps(registry), encoding="utf-8")

    def test_master_session_schemas_are_registered(self) -> None:
        from suite.contracts import validate_contract

        orientation = {
            "schema_version": "orientation_v1",
            "session_id": "ms-unit-root",
            "scope": "ROOT",
            "started_at": "2026-05-19T00:00:00Z",
            "git_snapshot": {"branch": None, "head": None, "status_lines": [], "recent_commits": []},
            "reads": [],
            "status_snapshot_path": "status-snapshot.json",
        }
        handoff = {
            "schema_version": "handoff_v1",
            "session_id": "ms-unit-root",
            "scope": "ROOT",
            "ended_at": "2026-05-19T00:00:00Z",
            "mode": "handoff",
            "authority_level": "source-verified",
            "git_state": {"branch": None, "head": None, "diff_since_orient": []},
            "what_checked": [],
            "what_changed": [],
            "next_action": "Continue.",
            "unresolved_risks": [],
        }
        compliance = {
            "schema_version": "compliance_v1",
            "session_id": "ms-unit-root",
            "verified_at": "2026-05-19T00:00:00Z",
            "rules": [{"name": "orientation_present", "status": "pass", "evidence": "orientation.json"}],
            "overall": "pass",
        }

        self.assertEqual(validate_contract("orientation", orientation), [])
        self.assertEqual(validate_contract("handoff", handoff), [])
        self.assertEqual(validate_contract("compliance", compliance), [])

    def test_orient_writes_orientation_and_index(self) -> None:
        from suite.master_session import orient

        summary = orient(self.temp_dir, scope="ROOT", session_id="ms-unit-root", force=True)

        session_dir = self.temp_dir / "runs" / "master-sessions" / "ms-unit-root"
        orientation = json.loads((session_dir / "orientation.json").read_text(encoding="utf-8"))
        index_rows = (self.temp_dir / "runs" / "master-sessions" / "index.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(summary["status"], "oriented")
        self.assertEqual(orientation["scope"], "ROOT")
        self.assertEqual({read["status"] for read in orientation["reads"]}, {"present"})
        self.assertTrue((session_dir / "status-snapshot.json").exists())
        self.assertEqual(len(index_rows), 1)

    def test_verify_fails_when_required_read_is_missing(self) -> None:
        from suite.master_session import orient, verify

        (self.temp_dir / "docs" / "workflow-stack.md").unlink()
        orient(self.temp_dir, scope="ROOT", session_id="ms-missing-read", force=True)

        report = verify(self.temp_dir, session_id="ms-missing-read")

        self.assertEqual(report["overall"], "fail")
        rules = {rule["name"]: rule for rule in report["rules"]}
        self.assertEqual(rules["orientation_reads_complete"]["status"], "fail")

    def test_orient_scoped_session_reads_registered_project_pack(self) -> None:
        from suite.master_session import orient

        pack_dir = self.temp_dir / "packs" / "weather"
        (pack_dir / "docs").mkdir(parents=True)
        (pack_dir / "AGENTS.md").write_text("# Weather rules\n", encoding="utf-8")
        (pack_dir / "docs" / "session-handoff.md").write_text("# Weather handoff\n", encoding="utf-8")
        self._write_project_pack_registry("WEATHER", "packs/weather")

        orient(self.temp_dir, scope="weather", session_id="ms-weather", force=True)

        orientation = json.loads(
            (self.temp_dir / "runs" / "master-sessions" / "ms-weather" / "orientation.json").read_text(
                encoding="utf-8"
            )
        )
        reads = {(item.get("source", "repo"), item["path"]): item for item in orientation["reads"]}
        self.assertEqual(orientation["scope"], "WEATHER")
        self.assertEqual(orientation["project_pack"]["status"], "resolved")
        self.assertEqual(orientation["project_pack"]["path"], str(pack_dir.resolve()))
        self.assertEqual(reads[("project_pack", "AGENTS.md")]["status"], "present")
        self.assertTrue(reads[("project_pack", "AGENTS.md")]["required"])
        self.assertEqual(reads[("project_pack", "docs/session-handoff.md")]["status"], "present")
        self.assertFalse(reads[("project_pack", "docs/session-handoff.md")]["required"])

    def test_orient_accepts_bom_encoded_project_pack_registry(self) -> None:
        from suite.master_session import orient

        pack_dir = self.temp_dir / "packs" / "weather"
        pack_dir.mkdir(parents=True)
        (pack_dir / "AGENTS.md").write_text("# Weather rules\n", encoding="utf-8")
        registry_dir = self.temp_dir / "configs" / "project-packs"
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry = {
            "schema_version": "project_pack_registry_v1",
            "packs": {"WEATHER": {"path": "packs/weather"}},
        }
        (registry_dir / "index.json").write_text(json.dumps(registry), encoding="utf-8-sig")

        orient(self.temp_dir, scope="WEATHER", session_id="ms-weather-bom", force=True)

        orientation = json.loads(
            (self.temp_dir / "runs" / "master-sessions" / "ms-weather-bom" / "orientation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(orientation["project_pack"]["status"], "resolved")

    def test_orient_resolves_local_project_pack_descriptor(self) -> None:
        from suite.master_session import orient

        pack_dir = self.temp_dir / "external" / "weather"
        pack_dir.mkdir(parents=True)
        (pack_dir / "AGENTS.md").write_text("# Weather rules\n", encoding="utf-8")
        descriptor_dir = self.temp_dir / "local" / "project-packs" / "weather"
        descriptor_dir.mkdir(parents=True)
        descriptor = {
            "id": "weather",
            "name": "Weather",
            "source_path": str(pack_dir),
            "isolation_mode": "git_worktree",
            "branch_prefix": "codex/",
            "allow_immediate_work": True,
            "allow_external_loop": False,
            "setup_command": None,
            "test_command": None,
            "lint_command": None,
            "build_command": None,
            "run_command": None,
            "notes": "",
        }
        (descriptor_dir / "project.json").write_text(json.dumps(descriptor), encoding="utf-8")

        orient(self.temp_dir, scope="WEATHER", session_id="ms-weather-local-pack", force=True)

        orientation = json.loads(
            (
                self.temp_dir
                / "runs"
                / "master-sessions"
                / "ms-weather-local-pack"
                / "orientation.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(orientation["project_pack"]["status"], "resolved")
        self.assertEqual(orientation["project_pack"]["path"], str(pack_dir.resolve()))
        self.assertEqual(
            orientation["project_pack"]["registry_path"],
            "local/project-packs/weather/project.json",
        )

    def test_verify_allows_missing_optional_project_pack_handoff(self) -> None:
        from suite.master_session import handoff, orient

        pack_dir = self.temp_dir / "packs" / "weather"
        pack_dir.mkdir(parents=True)
        (pack_dir / "AGENTS.md").write_text("# Weather rules\n", encoding="utf-8")
        self._write_project_pack_registry("WEATHER", "packs/weather")
        orient(self.temp_dir, scope="WEATHER", session_id="ms-weather-no-handoff", force=True)

        summary = handoff(
            self.temp_dir,
            session_id="ms-weather-no-handoff",
            next_action="Continue scoped work.",
            force=True,
        )

        rules = {rule["name"]: rule for rule in summary["compliance"]["rules"]}
        self.assertEqual(summary["compliance"]["overall"], "pass")
        self.assertEqual(rules["orientation_reads_complete"]["status"], "pass")

    def test_verify_fails_when_required_project_pack_read_is_missing(self) -> None:
        from suite.master_session import orient, verify

        pack_dir = self.temp_dir / "packs" / "weather"
        pack_dir.mkdir(parents=True)
        self._write_project_pack_registry("WEATHER", "packs/weather")
        orient(self.temp_dir, scope="WEATHER", session_id="ms-weather-missing-agents", force=True)

        report = verify(self.temp_dir, session_id="ms-weather-missing-agents")

        rules = {rule["name"]: rule for rule in report["rules"]}
        self.assertEqual(report["overall"], "fail")
        self.assertEqual(rules["orientation_reads_complete"]["status"], "fail")
        self.assertIn("project_pack:AGENTS.md", rules["orientation_reads_complete"]["evidence"])

    def test_handoff_writes_markdown_json_and_compliance(self) -> None:
        from suite.master_session import handoff, orient

        orient(self.temp_dir, scope="ROOT", session_id="ms-handoff", force=True)

        summary = handoff(
            self.temp_dir,
            session_id="ms-handoff",
            next_action="Continue with status command.",
            authority_level="source-verified",
            what_checked=["orientation"],
            what_changed=[],
            unresolved_risks=[],
            body="Body text.",
            force=True,
        )

        session_dir = self.temp_dir / "runs" / "master-sessions" / "ms-handoff"
        handoff_json = json.loads((session_dir / "handoff.json").read_text(encoding="utf-8"))
        compliance = json.loads((session_dir / "compliance.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "handoff_written")
        self.assertEqual(handoff_json["next_action"], "Continue with status command.")
        self.assertTrue((session_dir / "handoff.md").exists())
        self.assertEqual(compliance["overall"], "pass")

    def test_verify_fails_without_handoff(self) -> None:
        from suite.master_session import orient, verify

        orient(self.temp_dir, scope="ROOT", session_id="ms-no-handoff", force=True)

        report = verify(self.temp_dir, session_id="ms-no-handoff")

        self.assertEqual(report["overall"], "fail")
        rules = {rule["name"]: rule for rule in report["rules"]}
        self.assertEqual(rules["handoff_present"]["status"], "fail")

    def test_marker_log_passes_when_all_markers_are_present(self) -> None:
        from suite.master_session import handoff, log_marker, orient

        orient(self.temp_dir, scope="ROOT", session_id="ms-marker-pass", force=True)
        log_marker(self.temp_dir, session_id="ms-marker-pass", marker_ok=True, turn=1)
        log_marker(self.temp_dir, session_id="ms-marker-pass", marker_ok=True, turn=2)

        summary = handoff(self.temp_dir, session_id="ms-marker-pass", next_action="Stop.", force=True)

        rules = {rule["name"]: rule for rule in summary["compliance"]["rules"]}
        self.assertEqual(rules["marker_discipline"]["status"], "pass")

    def test_marker_log_fails_when_any_marker_is_missing(self) -> None:
        from suite.master_session import handoff, log_marker, orient

        orient(self.temp_dir, scope="ROOT", session_id="ms-marker-fail", force=True)
        log_marker(self.temp_dir, session_id="ms-marker-fail", marker_ok=True, turn=1)
        log_marker(self.temp_dir, session_id="ms-marker-fail", marker_ok=False, turn=2)

        summary = handoff(self.temp_dir, session_id="ms-marker-fail", next_action="Stop.", force=True)

        self.assertEqual(summary["compliance"]["overall"], "fail")
        rules = {rule["name"]: rule for rule in summary["compliance"]["rules"]}
        self.assertEqual(rules["marker_discipline"]["status"], "fail")
        self.assertIn("turn 2", rules["marker_discipline"]["evidence"])

    def test_marker_log_absent_is_skipped(self) -> None:
        from suite.master_session import handoff, orient

        orient(self.temp_dir, scope="ROOT", session_id="ms-no-marker-log", force=True)

        summary = handoff(self.temp_dir, session_id="ms-no-marker-log", next_action="Stop.", force=True)

        rules = {rule["name"]: rule for rule in summary["compliance"]["rules"]}
        self.assertEqual(rules["marker_discipline"]["status"], "skip")
        self.assertEqual(summary["compliance"]["overall"], "pass")

    def test_status_lists_open_and_closed_sessions(self) -> None:
        from suite.master_session import handoff, orient, status

        orient(self.temp_dir, scope="ROOT", session_id="ms-open", force=True)
        orient(self.temp_dir, scope="ROOT", session_id="ms-closed", force=True)
        handoff(self.temp_dir, session_id="ms-closed", next_action="Stop.", force=True)

        report = status(self.temp_dir)

        self.assertEqual(report["status"], "ok")
        self.assertIn("ms-open", report["open_session_ids"])
        self.assertIn("ms-closed", report["closed_session_ids"])

    def test_master_cli_orient_handoff_verify_and_status(self) -> None:
        orient_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "master",
                "orient",
                "--repo-root",
                str(self.temp_dir),
                "--scope",
                "ROOT",
                "--run-id",
                "ms-cli",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(orient_result.returncode, 0, orient_result.stderr)
        self.assertEqual(json.loads(orient_result.stdout)["session_id"], "ms-cli")

        handoff_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "master",
                "handoff",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "ms-cli",
                "--next-action",
                "Continue.",
                "--authority-level",
                "source-verified",
                "--what-checked",
                "orientation",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(handoff_result.returncode, 0, handoff_result.stderr)

        verify_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "master",
                "verify",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "ms-cli",
                "--strict",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(verify_result.returncode, 0, verify_result.stderr)
        self.assertEqual(json.loads(verify_result.stdout)["overall"], "pass")

        status_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "master",
                "status",
                "--repo-root",
                str(self.temp_dir),
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(status_result.returncode, 0, status_result.stderr)
        self.assertIn("ms-cli", json.loads(status_result.stdout)["closed_session_ids"])

    def test_master_cli_marker_appends_marker_log(self) -> None:
        from suite.master_session import handoff, orient

        orient(self.temp_dir, scope="ROOT", session_id="ms-cli-marker", force=True)

        marker_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "master",
                "marker",
                "--repo-root",
                str(self.temp_dir),
                "--session-id",
                "ms-cli-marker",
                "--turn",
                "1",
                "--marker-ok",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(marker_result.returncode, 0, marker_result.stderr)
        self.assertEqual(json.loads(marker_result.stdout)["status"], "marker_logged")

        summary = handoff(self.temp_dir, session_id="ms-cli-marker", next_action="Stop.", force=True)
        rules = {rule["name"]: rule for rule in summary["compliance"]["rules"]}
        self.assertEqual(rules["marker_discipline"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
