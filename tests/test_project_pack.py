import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.project_pack import (
    ProjectPackError,
    ensure_pack_directories,
    load_project_pack,
    map_project,
    prepare_project_pack,
)


ROOT = Path(__file__).resolve().parents[1]


class ProjectPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="project-pack-test-"))
        self.source = self.temp_dir / "target"
        self.source.mkdir()
        self.pack_dir = self.temp_dir / "pack"
        self.pack_dir.mkdir()
        self.pack_path = self.pack_dir / "project.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_pack(self, **overrides: object) -> None:
        data = {
            "id": "sample-app",
            "name": "Sample App",
            "source_path": str(self.source),
            "isolation_mode": "git_worktree",
            "branch_prefix": "codex/",
            "allow_immediate_work": True,
            "allow_external_loop": False,
        }
        data.update(overrides)
        self.pack_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_load_project_pack_accepts_required_fields_and_unknown_fields(self) -> None:
        self._write_pack(notes="local note", extra_future_field={"enabled": True})

        pack = load_project_pack(self.pack_path)

        self.assertEqual(pack.id, "sample-app")
        self.assertEqual(pack.name, "Sample App")
        self.assertEqual(pack.source_path, self.source)
        self.assertEqual(pack.isolation_mode, "git_worktree")
        self.assertEqual(pack.branch_prefix, "codex/")
        self.assertTrue(pack.allow_immediate_work)
        self.assertFalse(pack.allow_external_loop)
        self.assertEqual(pack.pack_dir, self.pack_dir)
        self.assertEqual(pack.raw["extra_future_field"], {"enabled": True})

    def test_load_project_pack_rejects_missing_required_field(self) -> None:
        self._write_pack()
        data = json.loads(self.pack_path.read_text(encoding="utf-8"))
        del data["source_path"]
        self.pack_path.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaisesRegex(ProjectPackError, "missing required field: source_path"):
            load_project_pack(self.pack_path)

    def test_load_project_pack_rejects_missing_source_path(self) -> None:
        self._write_pack(source_path=str(self.temp_dir / "missing"))

        with self.assertRaisesRegex(ProjectPackError, "source path does not exist"):
            load_project_pack(self.pack_path)

    def test_load_project_pack_rejects_unsupported_isolation_mode(self) -> None:
        self._write_pack(isolation_mode="copy")

        with self.assertRaisesRegex(ProjectPackError, "unsupported isolation_mode"):
            load_project_pack(self.pack_path)

    def test_ensure_pack_directories_creates_control_plane_folders(self) -> None:
        self._write_pack()
        pack = load_project_pack(self.pack_path)

        created = ensure_pack_directories(pack)

        self.assertEqual(created["map_dir"], self.pack_dir / "map")
        self.assertEqual(created["runs_dir"], self.pack_dir / "runs")
        self.assertEqual(created["lessons_dir"], self.pack_dir / "lessons")
        self.assertTrue((self.pack_dir / "map").is_dir())
        self.assertTrue((self.pack_dir / "runs").is_dir())
        self.assertTrue((self.pack_dir / "lessons").is_dir())

    def test_map_project_writes_current_truth_artifacts(self) -> None:
        (self.source / "README.md").write_text("# Old Docs\n", encoding="utf-8")
        (self.source / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
        (self.source / "src").mkdir()
        (self.source / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
        self._write_pack()
        pack = load_project_pack(self.pack_path)
        ensure_pack_directories(pack)

        result = map_project(pack)

        self.assertEqual(result["project_id"], "sample-app")
        self.assertEqual(result["source_path"], str(self.source))
        self.assertIn("README.md", result["top_level_entries"])
        self.assertIn("pyproject.toml", result["manifest_files"])
        self.assertTrue((self.pack_dir / "map" / "project-map.md").exists())
        self.assertTrue((self.pack_dir / "map" / "source-inventory.json").exists())
        self.assertTrue((self.pack_dir / "map" / "commands.md").exists())
        self.assertTrue((self.pack_dir / "map" / "architecture-notes.md").exists())
        self.assertTrue((self.pack_dir / "map" / "open-questions.md").exists())
        project_map = (self.pack_dir / "map" / "project-map.md").read_text(encoding="utf-8")
        self.assertIn("Documentation is evidence, not truth.", project_map)
        self.assertIn("README.md", project_map)

    def _init_git_source(self) -> None:
        subprocess.run(["git", "init"], cwd=self.source, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.source, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.source, check=True)
        (self.source / "README.md").write_text("# Sample\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.source, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.source, check=True, capture_output=True)

    def test_prepare_project_pack_creates_worktree_and_run_artifact(self) -> None:
        self._init_git_source()
        self._write_pack()

        result = prepare_project_pack(self.pack_path, run_id="unit-prepare")
        finding = json.loads(
            (self.pack_dir / "runs" / "unit-prepare" / "findings.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )

        self.assertEqual(result["status"], "prepared")
        self.assertEqual(result["project_id"], "sample-app")
        self.assertEqual(result["findings"], [finding])
        self.assertEqual(finding["detector_id"], "suite.project_pack")
        self.assertEqual(finding["artifact_id"], "unit-prepare")
        self.assertEqual(finding["finding_type"], "project_pack_prepared")
        self.assertEqual(finding["severity"], "info")
        self.assertEqual(finding["required_approval_tier"], "none")
        self.assertTrue(Path(result["workspace_path"]).exists())
        self.assertIn("codex/sample-app-unit-prepare", result["branch"])
        self.assertTrue((self.pack_dir / "runs" / "unit-prepare" / "result.json").exists())
        self.assertTrue((self.pack_dir / "map" / "project-map.md").exists())

    def test_prepare_project_pack_fails_for_non_git_source(self) -> None:
        self._write_pack()

        with self.assertRaisesRegex(ProjectPackError, "source path is not a git repository"):
            prepare_project_pack(self.pack_path, run_id="unit-non-git")

    def test_prepare_project_pack_runs_configured_setup_and_test_commands(self) -> None:
        self._init_git_source()
        self._write_pack(
            setup_command=[
                sys.executable,
                "-c",
                "from pathlib import Path; Path('setup-ran.txt').write_text('setup', encoding='utf-8')",
            ],
            test_command=[
                sys.executable,
                "-c",
                "from pathlib import Path; assert Path('setup-ran.txt').read_text(encoding='utf-8') == 'setup'",
            ],
        )

        result = prepare_project_pack(self.pack_path, run_id="unit-commands")
        workspace = Path(result["workspace_path"])

        self.assertEqual(result["status"], "prepared")
        self.assertTrue((workspace / "setup-ran.txt").exists())
        self.assertEqual([item["name"] for item in result["command_results"]], ["setup_command", "test_command"])
        self.assertEqual([item["exit_code"] for item in result["command_results"]], [0, 0])

    def test_project_pack_prepare_cli_writes_json_summary(self) -> None:
        self._init_git_source()
        self._write_pack()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "project-pack-prepare",
                "--pack",
                str(self.pack_path),
                "--run-id",
                "cli-prepare",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "prepared")
        self.assertEqual(summary["project_id"], "sample-app")
        self.assertTrue((self.pack_dir / "runs" / "cli-prepare" / "result.json").exists())

    def test_repo_ignores_local_project_packs(self) -> None:
        completed = subprocess.run(
            ["git", "check-ignore", "local/project-packs/example/project.json"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_project_pack_templates_exist(self) -> None:
        template_dir = ROOT / "templates" / "project-pack"

        self.assertTrue((template_dir / "project.json").exists())
        self.assertTrue((template_dir / "brief.md").exists())
        self.assertTrue((template_dir / "rules.md").exists())
        self.assertTrue((ROOT / "docs" / "project-packs.md").exists())


if __name__ == "__main__":
    unittest.main()
