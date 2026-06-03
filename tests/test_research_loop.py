import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from suite.research_cards import write_research_card
from suite.research_extract import ExtractionRecord, cleanup_acquired_source, extract_source_text
from suite.research_sources import SourceRecord


class ResearchLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="research-loop-test-"))
        self.config_path = self.temp_dir / "research.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _source(self, **overrides: object) -> SourceRecord:
        data = {
            "source_id": "arxiv:2605.12345v1",
            "source_type": "paper",
            "provider": "arxiv",
            "title": "Reliable LLM Agent Evaluation",
            "canonical_url": "https://arxiv.org/abs/2605.12345v1",
            "arxiv_id": "2605.12345",
            "version": "v1",
            "published_at": "2026-05-16T00:00:00Z",
            "updated_at": "2026-05-17T00:00:00Z",
            "metadata": {"categories": ["cs.CL"]},
            "text_preview": "This paper introduces an evaluation benchmark for tool-using agents.",
            "links": ["https://github.com/example/agent-eval"],
            "warnings": [],
        }
        data.update(overrides)
        return SourceRecord(**data)

    def _openreview_source(self) -> SourceRecord:
        return self._source(
            source_id="openreview:note-1",
            source_type="review-thread",
            provider="openreview",
            title="OpenReview Agent Evaluation",
            canonical_url="https://openreview.net/forum?id=forum-1",
            arxiv_id=None,
            version=None,
            metadata={"forum": "forum-1"},
            links=[],
        )

    def _configured_url_source(self) -> SourceRecord:
        return self._source(
            source_id="configured-url:https://example.com/research",
            provider="configured-url",
            title="Configured URL Agent Evaluation",
            canonical_url="https://example.com/research",
            arxiv_id=None,
            version=None,
            metadata={},
            links=["https://example.com/research"],
        )

    def _write_config(
        self,
        caps_overrides: dict[str, int] | None = None,
        research_runs_dir: str = "research-runs",
    ) -> None:
        caps = {
            "max_discovered_sources": 100,
            "max_acquired_sources": 20,
            "max_download_bytes": 50000000,
            "max_extracted_words_per_source": 2000,
            "max_total_extracted_words": 20000,
            "max_repo_clones": 2,
            "max_runtime_seconds": 300,
            "max_distillation_tokens": 12000,
            "max_synthesis_tokens": 8000,
        }
        if caps_overrides:
            caps.update(caps_overrides)
        data = {
            "providers": {
                "arxiv": {"enabled": True, "categories": ["cs.CL"]},
                "configured_urls": {"enabled": False, "urls": []},
                "openreview": {"enabled": False, "venues": []},
                "local": {"enabled": True, "paths": []},
            },
            "topic_keywords": ["agent", "evaluation"],
            "research_runs_dir": research_runs_dir,
            "cache_dir": "local/research-cache",
            "retention": {
                "keep_acquired_sources": False,
                "keep_failed_sources": True,
                "cleanup_after_extraction": True,
                "max_cache_bytes": 25000000,
            },
            "caps": caps,
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
        self.config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read_text_preserving_newline(self, path: Path) -> str:
        with path.open("r", encoding="utf-8", newline="") as file:
            return file.read()

    def test_run_research_loop_writes_scan_artifacts(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="unit-scan",
            force=True,
            provider_sources={"arxiv": [self._source()]},
        )

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["mode"], "scan-arxiv")
        run_dir = self.temp_dir / "research-runs" / "unit-scan"
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "discovered-sources.jsonl").exists())
        self.assertTrue((run_dir / "acquired-sources.jsonl").exists())
        self.assertTrue((run_dir / "extracted-sources.jsonl").exists())
        self.assertTrue((run_dir / "summary.json").exists())
        self.assertEqual(len(list((run_dir / "cards").glob("*.md"))), 1)
        discovered_lines = (run_dir / "discovered-sources.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(discovered_lines), 1)
        self.assertEqual(summary["card_count"], 1)

    def test_synthesize_week_writes_digest_and_candidate(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()
        run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="scan-one",
            force=True,
            provider_sources={"arxiv": [self._source()]},
        )

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="synthesize-week",
            run_id="week-one",
            force=True,
            provider_sources={},
        )

        run_dir = self.temp_dir / "research-runs" / "week-one"
        self.assertEqual(summary["status"], "completed")
        self.assertTrue((run_dir / "synthesis.md").exists())
        self.assertTrue((run_dir / "weekly-digest.md").exists())
        self.assertTrue((run_dir / "candidates").is_dir())
        self.assertTrue((run_dir / "summary.json").exists())
        digest_text = (run_dir / "weekly-digest.md").read_text(encoding="utf-8")
        self.assertIn("Reliable LLM Agent Evaluation", digest_text)
        self.assertIn("synthesis", summary)
        self.assertEqual(summary["synthesis"]["weekly_digest"], str(run_dir / "weekly-digest.md"))
        self.assertTrue(summary["synthesis"]["candidates"])
        candidate_text = Path(summary["synthesis"]["candidates"][0]).read_text(encoding="utf-8")
        self.assertIn("../scan-one/cards/", candidate_text)
        self.assertNotIn("C:\\", candidate_text)
        self.assertNotIn(str(self.temp_dir), candidate_text)
        self.assertIn("Unranked Prior Cards", candidate_text)
        self.assertNotIn("strongest", candidate_text.lower())

    def test_synthesize_week_without_prior_cards_writes_empty_digest_without_candidate(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="synthesize-week",
            run_id="week-empty",
            force=True,
            provider_sources={},
        )

        run_dir = self.temp_dir / "research-runs" / "week-empty"
        digest_text = (run_dir / "weekly-digest.md").read_text(encoding="utf-8")
        synthesis_text = (run_dir / "synthesis.md").read_text(encoding="utf-8")
        self.assertEqual(summary["card_count"], 0)
        self.assertEqual(summary["synthesis"]["candidates"], [])
        self.assertFalse((run_dir / "candidates" / "research-followup.md").exists())
        self.assertIn("No prior cards found.", digest_text)
        self.assertIn("No prior cards found.", synthesis_text)

    def test_run_research_loop_refuses_existing_run_without_force(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()
        run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="unit-scan",
            force=True,
            provider_sources={"arxiv": [self._source()]},
        )

        with self.assertRaisesRegex(FileExistsError, "Research run already exists"):
            run_research_loop(
                suite_root=self.temp_dir,
                config_path=self.config_path,
                mode="scan-arxiv",
                run_id="unit-scan",
                force=False,
                provider_sources={"arxiv": [self._source()]},
            )

    def test_run_research_loop_force_removes_existing_read_only_run(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()
        run_dir = self.temp_dir / "research-runs" / "unit-force"
        read_only_file = run_dir / "old" / "readonly.txt"
        read_only_file.parent.mkdir(parents=True)
        read_only_file.write_text("locked", encoding="utf-8")
        read_only_file.chmod(stat.S_IREAD)
        self.addCleanup(lambda: os.chmod(read_only_file, stat.S_IWRITE) if read_only_file.exists() else None)

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="unit-force",
            force=True,
            provider_sources={"arxiv": [self._source()]},
        )

        self.assertEqual(summary["status"], "completed")
        self.assertTrue((run_dir / "summary.json").exists())
        self.assertFalse(read_only_file.exists())

    def test_run_research_loop_offline_skips_live_providers_and_writes_empty_artifacts(self) -> None:
        import suite.research_loop as research_loop

        self._write_config()

        with patch.object(research_loop, "ArxivProvider", side_effect=AssertionError("live provider called")):
            summary = research_loop.run_research_loop(
                suite_root=self.temp_dir,
                config_path=self.config_path,
                mode="scan-arxiv",
                run_id="unit-offline",
                force=True,
                offline=True,
            )

        run_dir = self.temp_dir / "research-runs" / "unit-offline"
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["discovered_count"], 0)
        self.assertTrue(any("offline" in warning.lower() for warning in summary["warnings"]))
        self.assertTrue((run_dir / "discovered-sources.jsonl").exists())
        self.assertTrue((run_dir / "acquired-sources.jsonl").exists())
        self.assertTrue((run_dir / "extracted-sources.jsonl").exists())
        self.assertTrue((run_dir / "summary.json").exists())

    def test_run_research_loop_records_live_provider_failure_and_writes_summary(self) -> None:
        import suite.research_loop as research_loop

        class FailingProvider:
            def __init__(self, _categories: list[str]) -> None:
                pass

            def discover(self, _max_results: int) -> list[SourceRecord]:
                raise RuntimeError("provider down")

        self._write_config()

        with patch.object(research_loop, "ArxivProvider", FailingProvider):
            summary = research_loop.run_research_loop(
                suite_root=self.temp_dir,
                config_path=self.config_path,
                mode="scan-arxiv",
                run_id="unit-provider-failure",
                force=True,
            )

        run_dir = self.temp_dir / "research-runs" / "unit-provider-failure"
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["discovered_count"], 0)
        self.assertTrue(any("provider down" in warning for warning in summary["warnings"]))
        self.assertTrue((run_dir / "discovered-sources.jsonl").exists())
        self.assertTrue((run_dir / "summary.json").exists())

    def test_run_research_loop_records_provider_cooldown_on_rate_limit(self) -> None:
        import suite.research_loop as research_loop
        from suite.research_sources import ResearchProviderRateLimitError

        class RateLimitedProvider:
            name = "arxiv"

            def __init__(self, _categories: list[str]) -> None:
                pass

            def discover(self, _max_results: int) -> list[SourceRecord]:
                raise ResearchProviderRateLimitError(
                    "arxiv provider rate limited (HTTP 429); Retry-After: 120",
                    retry_after_seconds=120,
                )

        self._write_config()

        with patch.object(research_loop, "ArxivProvider", RateLimitedProvider):
            summary = research_loop.run_research_loop(
                suite_root=self.temp_dir,
                config_path=self.config_path,
                mode="scan-arxiv",
                run_id="unit-provider-cooldown-recorded",
                force=True,
            )

        run_dir = self.temp_dir / "research-runs" / "unit-provider-cooldown-recorded"
        state = json.loads((self.temp_dir / "research-runs" / "state.json").read_text(encoding="utf-8"))
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        event = summary["provider_events"][0]
        cooldown = state["provider_cooldowns"]["arxiv"]
        self.assertEqual(summary["discovered_count"], 0)
        self.assertEqual(event["type"], "provider_cooldown_recorded")
        self.assertEqual(event["provider"], "arxiv")
        self.assertEqual(event["retry_after_seconds"], 120)
        self.assertIn("cooldown_until", event)
        self.assertIn("rate limited", event["last_error"])
        self.assertEqual(cooldown, event)
        self.assertEqual(manifest["provider_events"], summary["provider_events"])

    def test_run_research_loop_skips_arxiv_when_provider_cooldown_active(self) -> None:
        import suite.research_loop as research_loop

        self._write_config()
        state_path = self.temp_dir / "research-runs" / "state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps(
                {
                    "sources": {},
                    "provider_cooldowns": {
                        "arxiv": {
                            "type": "provider_cooldown_recorded",
                            "provider": "arxiv",
                            "cooldown_until": "2999-01-01T00:00:00Z",
                            "retry_after_seconds": 120,
                            "last_error": "arxiv provider rate limited (HTTP 429)",
                            "updated_at": "2026-05-19T00:00:00Z",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        with patch.object(research_loop, "ArxivProvider", side_effect=AssertionError("live arxiv called")):
            summary = research_loop.run_research_loop(
                suite_root=self.temp_dir,
                config_path=self.config_path,
                mode="scan-arxiv",
                run_id="unit-provider-cooldown-active",
                force=True,
            )

        event = summary["provider_events"][0]
        self.assertEqual(summary["discovered_count"], 0)
        self.assertEqual(event["type"], "provider_cooldown_active")
        self.assertEqual(event["provider"], "arxiv")
        self.assertEqual(event["cooldown_until"], "2999-01-01T00:00:00Z")
        self.assertTrue(any("cooldown active" in warning for warning in summary["warnings"]))

    def test_run_research_loop_rejects_negative_overrides_before_creating_run_dir(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()

        for name, kwargs in [
            ("max_sources", {"max_sources": -1}),
            ("max_download_bytes", {"max_download_bytes": -1}),
        ]:
            with self.subTest(name=name):
                run_id = f"unit-negative-{name}"
                with self.assertRaisesRegex(ValueError, name):
                    run_research_loop(
                        suite_root=self.temp_dir,
                        config_path=self.config_path,
                        mode="scan-arxiv",
                        run_id=run_id,
                        force=True,
                        provider_sources={"arxiv": [self._source()]},
                        **kwargs,
                    )
                self.assertFalse((self.temp_dir / "research-runs" / run_id).exists())

    def test_research_runs_dir_override_must_be_dedicated_research_runs_root(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()
        sentinel = self.temp_dir / "tasks" / "sentinel.txt"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("keep", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "research_runs_dir_override"):
            run_research_loop(
                suite_root=self.temp_dir,
                config_path=self.config_path,
                mode="synthesize-week",
                run_id="tasks",
                force=True,
                research_runs_dir_override=self.temp_dir,
            )

        self.assertTrue(sentinel.exists())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_configured_research_runs_dir_must_not_allow_workspace_deletion(self) -> None:
        from suite.research_config import ResearchConfigError
        from suite.research_loop import run_research_loop

        self._write_config(research_runs_dir=".")
        sentinel = self.temp_dir / "tasks" / "sentinel.txt"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("keep", encoding="utf-8")

        with self.assertRaisesRegex(ResearchConfigError, "research-runs"):
            run_research_loop(
                suite_root=self.temp_dir,
                config_path=self.config_path,
                mode="scan-arxiv",
                run_id="tasks",
                force=True,
                provider_sources={"arxiv": [self._source()]},
            )

        self.assertTrue(sentinel.exists())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_run_research_loop_max_total_extracted_words_records_cap_event(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config(caps_overrides={"max_total_extracted_words": 12})
        first = self._source(
            source_id="arxiv:2605.00001v1",
            title="Agent Evaluation One",
            canonical_url="https://arxiv.org/abs/2605.00001v1",
            arxiv_id="2605.00001",
            text_preview="agent evaluation alpha beta gamma delta",
        )
        second = self._source(
            source_id="arxiv:2605.00002v1",
            title="Agent Evaluation Two",
            canonical_url="https://arxiv.org/abs/2605.00002v1",
            arxiv_id="2605.00002",
            text_preview="agent evaluation epsilon zeta eta theta",
        )

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="unit-total-cap",
            force=True,
            provider_sources={"arxiv": [first, second]},
        )

        manifest = json.loads(
            (self.temp_dir / "research-runs" / "unit-total-cap" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(summary["extracted_count"], 1)
        self.assertTrue(summary["cap_events"])
        self.assertTrue(any("max_total_extracted_words" in warning for warning in summary["warnings"]))
        self.assertEqual(manifest["cap_events"], summary["cap_events"])

    def test_run_research_loop_filters_injected_provider_sources_by_mode(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()
        arxiv_source = self._source()
        openreview_source = self._source(
            source_id="openreview:note-1",
            source_type="review-thread",
            provider="openreview",
            canonical_url="https://openreview.net/forum?id=forum-1",
            arxiv_id=None,
            version=None,
            metadata={"forum": "forum-1"},
            links=[],
        )

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="unit-filtered",
            force=True,
            provider_sources={"arxiv": [arxiv_source], "openreview": [openreview_source]},
        )

        discovered_path = self.temp_dir / "research-runs" / "unit-filtered" / "discovered-sources.jsonl"
        discovered_rows = [json.loads(line) for line in discovered_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(summary["discovered_count"], 1)
        self.assertEqual(discovered_rows[0]["provider"], "arxiv")

    def test_scan_conferences_accepts_injected_openreview_and_configured_url_sources(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-conferences",
            run_id="unit-conferences",
            force=True,
            metadata_only=True,
            provider_sources={
                "openreview": [self._openreview_source()],
                "configured-url": [self._configured_url_source()],
                "arxiv": [self._source()],
            },
        )

        discovered_path = self.temp_dir / "research-runs" / "unit-conferences" / "discovered-sources.jsonl"
        discovered_rows = [json.loads(line) for line in discovered_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(summary["discovered_count"], 2)
        self.assertEqual(
            {row["provider"] for row in discovered_rows},
            {"openreview", "configured-url"},
        )

    def test_slow_sweep_accepts_injected_arxiv_openreview_and_configured_url_sources(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="slow-sweep",
            run_id="unit-slow-sweep",
            force=True,
            metadata_only=True,
            provider_sources={
                "arxiv": [self._source()],
                "openreview": [self._openreview_source()],
                "configured-url": [self._configured_url_source()],
            },
        )

        discovered_path = self.temp_dir / "research-runs" / "unit-slow-sweep" / "discovered-sources.jsonl"
        discovered_rows = [json.loads(line) for line in discovered_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(summary["discovered_count"], 3)
        self.assertEqual(
            {row["provider"] for row in discovered_rows},
            {"arxiv", "openreview", "configured-url"},
        )

    def test_run_research_loop_skips_duplicate_canonical_sources_in_run_artifacts(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()
        first = self._source(
            source_id="raw-arxiv-primary",
            title="Primary Agent Evaluation",
            links=["https://github.com/example/primary"],
        )
        duplicate = self._source(
            source_id="raw-arxiv-duplicate",
            title="Duplicate Agent Evaluation",
            links=["https://github.com/example/duplicate"],
        )

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="unit-duplicates",
            force=True,
            provider_sources={"arxiv": [first, duplicate]},
        )

        run_dir = self.temp_dir / "research-runs" / "unit-duplicates"
        discovered_lines = (run_dir / "discovered-sources.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(summary["discovered_count"], 1)
        self.assertEqual(summary["extracted_count"], 1)
        self.assertEqual(summary["card_count"], 1)
        self.assertEqual(len(summary["cards"]), 1)
        self.assertEqual(len(list((run_dir / "cards").glob("*.md"))), 1)
        self.assertEqual(len(discovered_lines), 1)
        duplicate_signals = " ".join(summary["warnings"]) + " " + json.dumps(summary["cap_events"])
        self.assertIn("duplicate", duplicate_signals)
        self.assertIn("skipped", duplicate_signals)

    def test_run_research_loop_uses_highest_scoring_duplicate_for_artifacts(self) -> None:
        from suite.research_loop import run_research_loop

        self._write_config()
        low_score = self._source(
            source_id="raw-low-score",
            title="Unrelated Systems Note",
            text_preview="A short note about generic systems.",
            links=[],
        )
        high_score = self._source(
            source_id="raw-high-score",
            title="Agent Evaluation With Code",
            text_preview="A benchmark for agent evaluation with reproducible tooling.",
            links=["https://github.com/example/high-score"],
        )

        summary = run_research_loop(
            suite_root=self.temp_dir,
            config_path=self.config_path,
            mode="scan-arxiv",
            run_id="unit-best-duplicate",
            force=True,
            provider_sources={"arxiv": [low_score, high_score]},
        )

        run_dir = self.temp_dir / "research-runs" / "unit-best-duplicate"
        discovered_rows = [
            json.loads(line) for line in (run_dir / "discovered-sources.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        card_files = list((run_dir / "cards").glob("*.md"))
        self.assertEqual(summary["discovered_count"], 1)
        self.assertEqual(summary["extracted_count"], 1)
        self.assertEqual(summary["card_count"], 1)
        self.assertEqual(len(discovered_rows), 1)
        self.assertEqual(discovered_rows[0]["title"], "Agent Evaluation With Code")
        self.assertIn("https://github.com/example/high-score", discovered_rows[0]["links"])
        self.assertEqual(len(card_files), 1)
        card_text = card_files[0].read_text(encoding="utf-8")
        self.assertIn("Agent Evaluation With Code", card_text)
        self.assertIn("https://github.com/example/high-score", card_text)
        duplicate_signals = " ".join(summary["warnings"]) + " " + json.dumps(summary["cap_events"])
        self.assertIn("duplicate", duplicate_signals)

    def test_extract_source_text_writes_normalized_text_and_hash(self) -> None:
        output_dir = self.temp_dir / "extract"
        max_words = 8

        record = extract_source_text(self._source(), output_dir=output_dir, max_words=max_words)

        output_path = Path(record.normalized_text_path)
        self.assertTrue(output_path.exists())
        written_text = self._read_text_preserving_newline(output_path)
        expected_text = "# Reliable LLM Agent Evaluation This paper introduces\n"
        self.assertEqual(record.source_id, "arxiv:2605.12345v1")
        with self.subTest("payload"):
            self.assertEqual(written_text, expected_text)
        self.assertEqual(len(written_text.strip().split()), record.word_count)
        self.assertEqual(record.word_count, max_words)
        with self.subTest("hash"):
            self.assertEqual(record.source_hash, hashlib.sha256(written_text.encode("utf-8")).hexdigest())

    def test_write_research_card_includes_compact_fields(self) -> None:
        cards_dir = self.temp_dir / "cards"
        extraction = ExtractionRecord(
            source_id="arxiv:2605.12345v1",
            normalized_text_path=str(self.temp_dir / "text.txt"),
            source_hash="abc123",
            word_count=10,
            sections=[],
            status="extracted",
            warnings=[],
        )

        path = write_research_card(
            cards_dir,
            self._source(),
            extraction,
            score=7,
            score_reasons=["tier:fast-research", "keyword:agent"],
        )

        text = path.read_text(encoding="utf-8")
        self.assertIn("source_id: arxiv:2605.12345v1", text)
        self.assertIn("trust_tier: fast-research", text)
        self.assertIn("recommended_next_action:", text)

    def test_cleanup_acquired_source_deletes_cache_file_and_refuses_reference_repo(self) -> None:
        cache_root = self.temp_dir / "local" / "research-cache"
        cache_root.mkdir(parents=True)
        acquired = cache_root / "paper.pdf"
        acquired.write_text("raw", encoding="utf-8")
        references_repo = self.temp_dir / "references" / "repos" / "external"
        references_repo.mkdir(parents=True)

        cleanup_acquired_source(acquired, cache_root=cache_root)

        self.assertFalse(acquired.exists())
        with self.assertRaisesRegex(ValueError, "outside research cache"):
            cleanup_acquired_source(references_repo, cache_root=cache_root)

    def test_cleanup_acquired_source_refuses_cache_root_and_preserves_contents(self) -> None:
        cache_root = self.temp_dir / "local" / "research-cache"
        cache_root.mkdir(parents=True)
        sentinel = cache_root / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")

        with self.assertRaises(ValueError):
            cleanup_acquired_source(cache_root, cache_root=cache_root)

        self.assertTrue(sentinel.exists())

    def test_research_artifact_paths_do_not_collide_for_similar_source_ids(self) -> None:
        output_dir = self.temp_dir / "extract"
        cards_dir = self.temp_dir / "cards"
        first_source = self._source(
            source_id="configured-url:https://example.com/a-b",
            provider="configured-url",
            canonical_url="https://example.com/a-b",
            arxiv_id=None,
            version=None,
        )
        second_source = self._source(
            source_id="configured-url:https://example.com/a_b",
            provider="configured-url",
            canonical_url="https://example.com/a_b",
            arxiv_id=None,
            version=None,
        )

        first_record = extract_source_text(first_source, output_dir=output_dir, max_words=20)
        second_record = extract_source_text(second_source, output_dir=output_dir, max_words=20)
        first_card = write_research_card(cards_dir, first_source, first_record, score=1, score_reasons=[])
        second_card = write_research_card(cards_dir, second_source, second_record, score=1, score_reasons=[])

        with self.subTest("extraction paths"):
            self.assertNotEqual(first_record.normalized_text_path, second_record.normalized_text_path)
        with self.subTest("card paths"):
            self.assertNotEqual(first_card, second_card)

    def test_research_artifact_paths_use_fallback_for_source_ids_without_safe_stem(self) -> None:
        source = self._source(
            source_id=":⚙️:—",
            provider="configured-url",
            canonical_url="https://example.com/source",
            arxiv_id=None,
            version=None,
        )
        record = extract_source_text(source, output_dir=self.temp_dir / "extract", max_words=20)
        card_path = write_research_card(self.temp_dir / "cards", source, record, score=1, score_reasons=[])

        self.assertRegex(Path(record.normalized_text_path).name, r"^source-[0-9a-f]{10}\.txt$")
        self.assertRegex(card_path.name, r"^source-[0-9a-f]{10}\.md$")

    def test_research_artifact_paths_bound_long_source_id_filenames(self) -> None:
        source_id = "configured-url:https://example.com/" + ("very-long-segment-" * 30)
        source = self._source(
            source_id=source_id,
            provider="configured-url",
            canonical_url="https://example.com/long",
            arxiv_id=None,
            version=None,
        )

        record = extract_source_text(source, output_dir=self.temp_dir / "extract", max_words=20)
        card_path = write_research_card(self.temp_dir / "cards", source, record, score=1, score_reasons=[])

        self.assertLessEqual(len(Path(record.normalized_text_path).name), 120)
        self.assertLessEqual(len(card_path.name), 120)

    def test_research_loop_cli_writes_json_summary(self) -> None:
        cli_temp = Path(tempfile.mkdtemp(prefix="research-loop-cli-", dir=ROOT))
        self.addCleanup(lambda: shutil.rmtree(cli_temp, ignore_errors=True))
        config_path = cli_temp / "research.json"
        research_runs_dir = cli_temp / "research-runs"
        self._write_config()
        shutil.copyfile(self.config_path, config_path)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "research-loop",
                "--mode",
                "synthesize-week",
                "--config",
                str(config_path),
                "--run-id",
                "cli-week",
                "--research-runs-dir",
                str(research_runs_dir),
                "--force",
                "--offline",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["mode"], "synthesize-week")
        self.assertTrue((research_runs_dir / "cli-week" / "summary.json").exists())

    def test_research_loop_cli_writes_scheduler_template_without_run_dir(self) -> None:
        cli_temp = Path(tempfile.mkdtemp(prefix="research-loop-schedule-", dir=ROOT))
        self.addCleanup(lambda: shutil.rmtree(cli_temp, ignore_errors=True))
        config_path = cli_temp / "research.json"
        research_runs_dir = cli_temp / "research-runs"
        self._write_config()
        shutil.copyfile(self.config_path, config_path)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "research-loop",
                "--mode",
                "scan-arxiv",
                "--config",
                str(config_path),
                "--run-id",
                "cli-template",
                "--research-runs-dir",
                str(research_runs_dir),
                "--write-scheduler-template",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        template = json.loads(result.stdout)
        self.assertEqual(template["status"], "template")
        argv = template["jobs"][0]["argv"]
        self.assertIsInstance(argv, list)
        self.assertIn(str(config_path.resolve()), argv)
        self.assertEqual(argv.count(str(config_path.resolve())), 1)
        self.assertIn("--metadata-only", argv)
        self.assertIn("--max-sources", argv)
        self.assertIn("25", argv)
        self.assertFalse((research_runs_dir / "cli-template").exists())

    def test_research_loop_cli_missing_config_reports_argparse_error_without_traceback(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "research-loop",
                "--mode",
                "synthesize-week",
                "--config",
                "missing-config.json",
                "--run-id",
                "missing",
                "--offline",
                "--force",
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
