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


class ResearchIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="research-intake-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_analyze_research_need_flags_current_protocol_and_repo_search(self) -> None:
        from suite.research_intake import analyze_research_need

        analysis = analyze_research_need(
            "Before building, check whether there is a current MCP tool, "
            "agent handoff protocol, or GitHub repo for LLM relay format evaluation.",
            source_name="chat",
        )

        self.assertEqual(analysis["status"], "research_needed")
        self.assertIn("current-information", analysis["trigger_ids"])
        self.assertIn("existing-work", analysis["trigger_ids"])
        self.assertIn("external-repository", analysis["trigger_ids"])
        self.assertIn("MCP", analysis["topics"])
        self.assertTrue(analysis["recommended_queries"])

    def test_analyze_research_need_ignores_local_mechanical_work(self) -> None:
        from suite.research_intake import analyze_research_need

        analysis = analyze_research_need("Rename a local variable in suite/cli.py.")

        self.assertEqual(analysis["status"], "research_not_needed")
        self.assertEqual(analysis["triggers"], [])
        self.assertEqual(analysis["recommended_queries"], [])

    def test_write_research_intake_run_writes_auditable_artifacts(self) -> None:
        from suite.research_intake import write_research_intake_run

        summary = write_research_intake_run(
            suite_root=self.temp_dir,
            text="Research current TOON, ONTO, MCP, and GitHub repos before designing a relay benchmark.",
            run_id="unit-intake",
            force=True,
            source_name="unit-test",
        )

        run_dir = self.temp_dir / "research-runs" / "unit-intake"
        self.assertEqual(summary["status"], "research_needed")
        self.assertEqual(summary["mode"], "research-intake")
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "input.md").exists())
        self.assertTrue((run_dir / "research-needed.json").exists())
        self.assertTrue((run_dir / "research-needed.md").exists())
        self.assertTrue((run_dir / "existing-work-prompt.md").exists())
        self.assertTrue((run_dir / "summary.json").exists())
        prompt = (run_dir / "existing-work-prompt.md").read_text(encoding="utf-8")
        self.assertIn("Do not invent citations", prompt)
        self.assertIn("TOON", prompt)

    def test_write_research_intake_run_refuses_existing_run_without_force(self) -> None:
        from suite.research_intake import write_research_intake_run

        write_research_intake_run(
            suite_root=self.temp_dir,
            text="Check current MCP repos.",
            run_id="existing",
            force=True,
        )

        with self.assertRaisesRegex(FileExistsError, "Research intake run already exists"):
            write_research_intake_run(
                suite_root=self.temp_dir,
                text="Check current MCP repos again.",
                run_id="existing",
                force=False,
            )

    def test_research_intake_cli_writes_json_summary(self) -> None:
        cli_temp = Path(tempfile.mkdtemp(prefix="research-intake-cli-", dir=ROOT))
        self.addCleanup(lambda: shutil.rmtree(cli_temp, ignore_errors=True))
        research_runs_dir = cli_temp / "research-runs"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "research-intake",
                "--text",
                "Find current GitHub repos and protocol specs for LLM handoff evaluation.",
                "--run-id",
                "cli-intake",
                "--research-runs-dir",
                str(research_runs_dir),
                "--force",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["mode"], "research-intake")
        self.assertEqual(summary["status"], "research_needed")
        self.assertTrue((research_runs_dir / "cli-intake" / "summary.json").exists())

    def test_research_intake_cli_missing_text_file_reports_argparse_error(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "research-intake",
                "--text-file",
                "missing-intake.md",
                "--run-id",
                "missing-file",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
