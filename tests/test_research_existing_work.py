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


class ResearchExistingWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="existing-work-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _github_payload(self) -> dict:
        return {
            "total_count": 2,
            "incomplete_results": False,
            "items": [
                {
                    "id": 101,
                    "full_name": "example/llm-handoff-bench",
                    "html_url": "https://github.com/example/llm-handoff-bench",
                    "description": "Benchmark LLM agent handoff formats.",
                    "stargazers_count": 321,
                    "forks_count": 17,
                    "open_issues_count": 4,
                    "language": "Python",
                    "topics": ["llm", "agents", "benchmark"],
                    "license": {"spdx_id": "MIT"},
                    "archived": False,
                    "fork": False,
                    "created_at": "2025-10-01T00:00:00Z",
                    "updated_at": "2026-05-18T00:00:00Z",
                    "pushed_at": "2026-05-17T00:00:00Z",
                    "homepage": "https://example.com/handoff-bench",
                },
                {
                    "id": 102,
                    "full_name": "old/example-handoff",
                    "html_url": "https://github.com/old/example-handoff",
                    "description": None,
                    "stargazers_count": 2,
                    "forks_count": 0,
                    "open_issues_count": 0,
                    "language": None,
                    "topics": [],
                    "license": None,
                    "archived": True,
                    "fork": False,
                    "created_at": "2021-01-01T00:00:00Z",
                    "updated_at": "2021-01-02T00:00:00Z",
                    "pushed_at": "2021-01-02T00:00:00Z",
                    "homepage": "",
                },
            ],
        }

    def test_normalize_github_repository_extracts_reuse_signals(self) -> None:
        from suite.research_existing_work import normalize_github_repository

        record = normalize_github_repository(self._github_payload()["items"][0])

        self.assertEqual(record["source_type"], "github-repository")
        self.assertEqual(record["name"], "example/llm-handoff-bench")
        self.assertEqual(record["url"], "https://github.com/example/llm-handoff-bench")
        self.assertEqual(record["license"], "MIT")
        self.assertEqual(record["stars"], 321)
        self.assertEqual(record["maturity"], "active")
        self.assertEqual(record["reuse_potential"], "high")
        self.assertIn("benchmark", record["evidence_tags"])

    def test_run_existing_work_discovery_writes_source_backed_artifacts(self) -> None:
        from suite.research_existing_work import run_existing_work_discovery

        summary = run_existing_work_discovery(
            suite_root=self.temp_dir,
            topic="LLM handoff benchmark",
            run_id="unit-existing",
            force=True,
            github_payloads=[self._github_payload()],
        )

        run_dir = self.temp_dir / "research-runs" / "unit-existing"
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["mode"], "research-existing-work")
        self.assertEqual(summary["source_count"], 2)
        self.assertEqual(summary["top_sources"][0]["name"], "example/llm-handoff-bench")
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "queries.json").exists())
        self.assertTrue((run_dir / "sources" / "github-repositories.json").exists())
        self.assertTrue((run_dir / "summary.md").exists())
        self.assertTrue((run_dir / "summary.json").exists())
        queries = json.loads((run_dir / "queries.json").read_text(encoding="utf-8"))
        self.assertEqual(queries["queries"], ["LLM handoff benchmark in:name,description"])
        cards = list((run_dir / "cards").glob("*.md"))
        self.assertEqual(len(cards), 2)
        self.assertIn("https://github.com/example/llm-handoff-bench", cards[0].read_text(encoding="utf-8"))

    def test_run_existing_work_discovery_reads_prior_intake_queries(self) -> None:
        from suite.research_existing_work import run_existing_work_discovery

        intake_dir = self.temp_dir / "research-runs" / "intake-one"
        intake_dir.mkdir(parents=True)
        (intake_dir / "research-needed.json").write_text(
            json.dumps(
                {
                    "recommended_queries": [
                        "LLM handoff benchmark existing open source GitHub repository",
                        "LLM handoff benchmark official documentation protocol specification",
                    ]
                }
            ),
            encoding="utf-8",
        )

        summary = run_existing_work_discovery(
            suite_root=self.temp_dir,
            intake_run="intake-one",
            run_id="from-intake",
            force=True,
            github_payloads=[self._github_payload(), {"total_count": 0, "incomplete_results": False, "items": []}],
        )

        queries = json.loads((self.temp_dir / "research-runs" / "from-intake" / "queries.json").read_text())
        self.assertEqual(summary["source_count"], 2)
        self.assertEqual(queries["input_source"]["intake_run"], "intake-one")
        self.assertEqual(len(queries["queries"]), 2)

    def test_run_existing_work_discovery_refuses_existing_run_without_force(self) -> None:
        from suite.research_existing_work import run_existing_work_discovery

        run_existing_work_discovery(
            suite_root=self.temp_dir,
            topic="LLM handoff benchmark",
            run_id="existing",
            force=True,
            github_payloads=[self._github_payload()],
        )

        with self.assertRaisesRegex(FileExistsError, "Existing-work discovery run already exists"):
            run_existing_work_discovery(
                suite_root=self.temp_dir,
                topic="LLM handoff benchmark",
                run_id="existing",
                force=False,
                github_payloads=[self._github_payload()],
            )

    def test_research_existing_work_cli_writes_json_summary_from_fixture(self) -> None:
        cli_temp = Path(tempfile.mkdtemp(prefix="existing-work-cli-", dir=ROOT))
        self.addCleanup(lambda: shutil.rmtree(cli_temp, ignore_errors=True))
        research_runs_dir = cli_temp / "research-runs"
        fixture_path = cli_temp / "github-search.json"
        fixture_path.write_text(json.dumps(self._github_payload()), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "research-existing-work",
                "--topic",
                "LLM handoff benchmark",
                "--run-id",
                "cli-existing",
                "--research-runs-dir",
                str(research_runs_dir),
                "--fixture-json",
                str(fixture_path),
                "--force",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["mode"], "research-existing-work")
        self.assertEqual(summary["source_count"], 2)
        self.assertTrue((research_runs_dir / "cli-existing" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
