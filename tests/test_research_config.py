import importlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ResearchConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="research-config-test-"))
        self.config_path = self.temp_dir / "research.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _research_config_module(self):
        try:
            return importlib.import_module("suite.research_config")
        except ModuleNotFoundError as exc:
            self.fail(f"suite.research_config is missing: {exc}")

    def _write_config(self, **overrides: object) -> None:
        data = {
            "providers": {
                "arxiv": {"enabled": True, "categories": ["cs.CL", "cs.AI", "cs.LG"]},
                "configured_urls": {"enabled": True, "urls": []},
                "openreview": {"enabled": False, "venues": []},
                "local": {"enabled": True, "paths": []},
            },
            "topic_keywords": [
                "agent",
                "LLM",
                "evaluation",
                "RAG",
                "alignment",
                "inference",
                "benchmark",
                "tool use",
            ],
            "research_runs_dir": "research-runs",
            "cache_dir": "local/research-cache",
            "retention": {
                "keep_acquired_sources": False,
                "keep_failed_sources": True,
                "cleanup_after_extraction": True,
                "max_cache_bytes": 25000000,
            },
            "caps": {
                "max_discovered_sources": 100,
                "max_acquired_sources": 20,
                "max_download_bytes": 50000000,
                "max_extracted_words_per_source": 2000,
                "max_total_extracted_words": 20000,
                "max_repo_clones": 2,
                "max_runtime_seconds": 300,
                "max_distillation_tokens": 12000,
                "max_synthesis_tokens": 8000,
            },
            "thresholds": {
                "metadata_only": 1,
                "extract": 4,
                "card": 6,
            },
            "schedule": {
                "timezone": "America/New_York",
                "jobs": [
                    {
                        "name": "nightly-arxiv-scan",
                        "mode": "scan-arxiv",
                        "days": ["sun", "mon", "tue", "wed", "thu"],
                        "time": "21:15",
                        "args": ["--metadata-only", "--max-sources", "25"],
                    },
                    {
                        "name": "weekday-community-scan",
                        "mode": "scan-community",
                        "days": ["mon", "tue", "wed", "thu", "fri"],
                        "time": "09:00",
                    },
                    {
                        "name": "openreview-conference-scan",
                        "mode": "scan-openreview",
                        "days": ["mon", "wed", "fri"],
                        "time": "11:30",
                    },
                    {
                        "name": "weekly-synthesis",
                        "mode": "synthesize-week",
                        "days": ["fri"],
                        "time": "15:00",
                    },
                    {
                        "name": "monthly-slow-sweep",
                        "mode": "slow-sweep",
                        "monthly": "first-monday",
                        "time": "10:00",
                    },
                ],
            },
        }
        data.update(overrides)
        self.config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_load_research_config_accepts_schedule_and_caps(self) -> None:
        module = self._research_config_module()
        self._write_config()

        config = module.load_research_config(self.config_path, suite_root=self.temp_dir)

        self.assertEqual(config.arxiv_categories, ["cs.CL", "cs.AI", "cs.LG"])
        self.assertEqual(
            config.topic_keywords,
            ["agent", "LLM", "evaluation", "RAG", "alignment", "inference", "benchmark", "tool use"],
        )
        self.assertEqual(config.research_runs_dir, self.temp_dir / "research-runs")
        self.assertEqual(config.cache_dir, self.temp_dir / "local" / "research-cache")
        self.assertEqual(config.schedule_timezone, "America/New_York")
        self.assertEqual(
            [job.name for job in config.schedule_jobs],
            [
                "nightly-arxiv-scan",
                "weekday-community-scan",
                "openreview-conference-scan",
                "weekly-synthesis",
                "monthly-slow-sweep",
            ],
        )
        self.assertEqual(config.caps["max_acquired_sources"], 20)
        self.assertEqual(config.thresholds["card"], 6)
        self.assertFalse(config.retention["keep_acquired_sources"])
        self.assertEqual(config.schedule_jobs[0].args, ("--metadata-only", "--max-sources", "25"))

    def test_load_research_config_accepts_openreview_venue_objects(self) -> None:
        module = self._research_config_module()
        invitation = "ICLR.cc/2026/Conference/-/Submission"
        self._write_config(
            providers={
                "arxiv": {"enabled": True, "categories": ["cs.CL", "cs.AI", "cs.LG"]},
                "configured_urls": {"enabled": True, "urls": []},
                "openreview": {"enabled": True, "venues": [{"invitation": invitation}]},
                "local": {"enabled": True, "paths": []},
            }
        )

        config = module.load_research_config(self.config_path, suite_root=self.temp_dir)

        self.assertEqual(config.providers["openreview"]["venues"][0]["invitation"], invitation)

    def test_load_research_config_rejects_malformed_openreview_venues(self) -> None:
        module = self._research_config_module()
        malformed_venues = [
            [{}],
            [{"invitation": ""}],
            [{"invitation": "   "}],
            ["ICLR.cc/2026/Conference/-/Submission"],
        ]

        for venues in malformed_venues:
            with self.subTest(venues=venues):
                self._write_config(
                    providers={
                        "arxiv": {"enabled": True, "categories": ["cs.CL", "cs.AI", "cs.LG"]},
                        "configured_urls": {"enabled": True, "urls": []},
                        "openreview": {"enabled": True, "venues": venues},
                        "local": {"enabled": True, "paths": []},
                    }
                )

                with self.assertRaisesRegex(module.ResearchConfigError, "providers.openreview.venues"):
                    module.load_research_config(self.config_path, suite_root=self.temp_dir)

    def test_load_research_config_rejects_path_outside_workspace(self) -> None:
        module = self._research_config_module()
        self._write_config(research_runs_dir=str(self.temp_dir.parent / "outside-runs"))

        with self.assertRaisesRegex(module.ResearchConfigError, "escapes suite workspace"):
            module.load_research_config(self.config_path, suite_root=self.temp_dir)

    def test_load_research_config_requires_dedicated_research_runs_directory(self) -> None:
        module = self._research_config_module()

        for research_runs_dir in [".", "tasks"]:
            with self.subTest(research_runs_dir=research_runs_dir):
                self._write_config(research_runs_dir=research_runs_dir)

                with self.assertRaisesRegex(module.ResearchConfigError, "dedicated research-runs directory"):
                    module.load_research_config(self.config_path, suite_root=self.temp_dir)

    def test_load_research_config_rejects_unknown_mode(self) -> None:
        module = self._research_config_module()
        self._write_config(
            schedule={
                "timezone": "America/New_York",
                "jobs": [{"name": "bad", "mode": "daemon", "days": ["mon"], "time": "09:00"}],
            }
        )

        with self.assertRaisesRegex(module.ResearchConfigError, "unsupported schedule mode: daemon"):
            module.load_research_config(self.config_path, suite_root=self.temp_dir)


if __name__ == "__main__":
    unittest.main()
