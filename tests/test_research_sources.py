import importlib
import json
import shutil
import sys
import tempfile
import urllib.error
import unittest
from email.message import Message
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ResearchSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="research-sources-test-"))
        self.state_path = self.temp_dir / "research-state.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _modules(self):
        try:
            return (
                importlib.import_module("suite.research_sources"),
                importlib.import_module("suite.research_state"),
                importlib.import_module("suite.research_score"),
            )
        except ModuleNotFoundError as exc:
            self.fail(f"research source module is missing: {exc}")

    def _source(self, **overrides: object):
        research_sources, _, _ = self._modules()
        data = {
            "source_id": "source-1",
            "source_type": "paper",
            "provider": "arxiv",
            "title": "Agent Evaluation Methods",
            "canonical_url": "https://arxiv.org/abs/2605.12345v2",
            "arxiv_id": "2605.12345",
            "version": "v2",
            "published_at": "2026-05-01",
            "updated_at": "2026-05-02",
            "metadata": {},
            "text_preview": "A benchmark for agent evaluation.",
            "links": [],
            "warnings": [],
        }
        data.update(overrides)
        return research_sources.SourceRecord(**data)

    def test_canonical_source_id_prefers_arxiv_id_and_version(self) -> None:
        _, research_state, _ = self._modules()
        source = self._source(arxiv_id="2605.12345", version="v2")

        source_id = research_state.canonical_source_id(source)

        self.assertEqual(source_id, "arxiv:2605.12345v2")

    def test_canonical_source_id_prefers_openreview_forum_over_note_id(self) -> None:
        _, research_state, _ = self._modules()
        source = self._source(
            provider="openreview",
            canonical_url="https://openreview.net/forum?id=forum-456",
            arxiv_id=None,
            version=None,
            metadata={"openreview_id": "note-123", "forum": "forum-456"},
        )

        source_id = research_state.canonical_source_id(source)

        self.assertEqual(source_id, "openreview:forum-456")

    def test_research_state_merges_duplicate_sources_by_canonical_id(self) -> None:
        _, research_state, _ = self._modules()
        state = research_state.ResearchState.load(self.state_path)
        arxiv_source = self._source(
            source_id="arxiv-source",
            provider="arxiv",
            links=["https://arxiv.org/pdf/2605.12345v2"],
            warnings=["abstract-truncated"],
        )
        community_source = self._source(
            source_id="hf-source",
            provider="huggingface",
            canonical_url="https://huggingface.co/papers/2605.12345",
            links=["https://github.com/example/agent-eval"],
            warnings=[],
        )

        first_id = state.upsert(arxiv_source)
        second_id = state.upsert(community_source)
        state.save()

        self.assertEqual(first_id, second_id)
        reloaded = research_state.ResearchState.load(self.state_path)
        self.assertEqual(list(reloaded.sources), ["arxiv:2605.12345v2"])
        merged = reloaded.sources["arxiv:2605.12345v2"]
        self.assertEqual(merged["providers"], ["arxiv", "huggingface"])
        self.assertIn("https://github.com/example/agent-eval", merged["links"])
        self.assertEqual(merged["warnings"], ["abstract-truncated"])

    def test_research_state_updates_source_snapshot_for_newer_duplicate(self) -> None:
        _, research_state, _ = self._modules()
        state = research_state.ResearchState.load(self.state_path)
        older_source = self._source(
            source_id="older-arxiv",
            provider="arxiv",
            title="Older Agent Evaluation Draft",
            canonical_url="https://arxiv.org/abs/2605.12345v2",
            published_at="2026-05-01",
            updated_at="2026-05-02",
            metadata={"abstract_source": "arxiv"},
            text_preview="Older preview text.",
            links=["https://arxiv.org/pdf/2605.12345v2"],
            warnings=["abstract-truncated"],
        )
        newer_source = self._source(
            source_id="newer-community",
            provider="huggingface",
            title="Newer Agent Evaluation Release",
            canonical_url="https://huggingface.co/papers/2605.12345",
            published_at="2026-05-03",
            updated_at="2026-05-04",
            metadata={"community_votes": 7, "summary_source": "huggingface"},
            text_preview="Newer preview text with community context.",
            links=["https://github.com/example/agent-eval"],
            warnings=["metadata-normalized"],
        )

        state.upsert(older_source)
        state.upsert(newer_source)
        state.save()

        reloaded = research_state.ResearchState.load(self.state_path)
        merged = reloaded.sources["arxiv:2605.12345v2"]
        snapshot = merged["source"]
        self.assertEqual(snapshot["provider"], "huggingface")
        self.assertEqual(snapshot["title"], "Newer Agent Evaluation Release")
        self.assertEqual(snapshot["canonical_url"], "https://huggingface.co/papers/2605.12345")
        self.assertEqual(snapshot["metadata"], {"community_votes": 7, "summary_source": "huggingface"})
        self.assertEqual(snapshot["text_preview"], "Newer preview text with community context.")
        self.assertEqual(snapshot["published_at"], "2026-05-03")
        self.assertEqual(snapshot["updated_at"], "2026-05-04")
        self.assertEqual(
            snapshot["links"],
            ["https://arxiv.org/pdf/2605.12345v2", "https://github.com/example/agent-eval"],
        )
        self.assertEqual(snapshot["warnings"], ["abstract-truncated", "metadata-normalized"])

    def test_research_state_rejects_invalid_json_with_clear_error(self) -> None:
        _, research_state, _ = self._modules()
        self.state_path.write_text("{not valid json", encoding="utf-8")

        with self.assertRaisesRegex(research_state.ResearchStateError, "invalid research state"):
            research_state.ResearchState.load(self.state_path)

    def test_score_source_records_reasons_for_relevant_paper_with_code(self) -> None:
        _, _, research_score = self._modules()
        source = self._source(
            title="Agent Evaluation Benchmarks",
            text_preview="A new protocol for evaluating language model agents.",
            links=["https://github.com/example/agent-eval"],
        )

        scored = research_score.score_source(source, ["agent", "evaluation", "alignment"])

        self.assertGreaterEqual(scored.score, 6)
        self.assertIn("tier:fast-research", scored.reasons)
        self.assertIn("keyword:agent", scored.reasons)
        self.assertIn("linked-code", scored.reasons)

    def test_arxiv_provider_parses_atom_entry(self) -> None:
        research_sources, _, _ = self._modules()
        atom_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2605.12345v2</id>
    <updated>2026-05-12T09:30:00Z</updated>
    <published>2026-05-10T09:30:00Z</published>
    <title>Agent Discovery Methods</title>
    <summary>A paper about research agents.</summary>
    <category term="cs.CL"/>
    <link href="http://arxiv.org/abs/2605.12345v2" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2605.12345v2" rel="related" type="application/pdf"/>
  </entry>
</feed>
"""

        provider = research_sources.ArxivProvider(
            ["cs.CL"],
            fetch_text=lambda _url: atom_feed,
            request_delay_seconds=0,
        )

        records = provider.discover(max_results=5)

        self.assertEqual(len(records), 1)
        source = records[0]
        self.assertEqual(source.arxiv_id, "2605.12345")
        self.assertEqual(source.version, "v2")
        self.assertEqual(source.metadata["categories"], ["cs.CL"])
        self.assertIn("http://arxiv.org/pdf/2605.12345v2", source.links)

    def test_arxiv_provider_rejects_atom_error_entry(self) -> None:
        research_sources, _, _ = self._modules()
        atom_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Error</title>
    <summary>Search query contains a bad query term.</summary>
  </entry>
</feed>
"""
        provider = research_sources.ArxivProvider(
            ["cs.CL"],
            fetch_text=lambda _url: atom_feed,
            request_delay_seconds=0,
        )

        with self.assertRaisesRegex(research_sources.ResearchProviderError, "arxiv|error"):
            provider.discover(max_results=5)

    def test_arxiv_provider_retries_transient_fetch_errors(self) -> None:
        research_sources, _, _ = self._modules()
        atom_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2605.12345v2</id>
    <updated>2026-05-12T09:30:00Z</updated>
    <published>2026-05-10T09:30:00Z</published>
    <title>Agent Discovery Methods</title>
    <summary>A paper about research agents.</summary>
    <category term="cs.CL"/>
    <link href="http://arxiv.org/abs/2605.12345v2" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""
        calls = []

        def flaky_fetch(_url: str) -> str:
            calls.append(_url)
            if len(calls) == 1:
                raise TimeoutError("The read operation timed out")
            return atom_feed

        provider = research_sources.ArxivProvider(
            ["cs.CL"],
            fetch_text=flaky_fetch,
            request_delay_seconds=0,
            retry_attempts=2,
            retry_delay_seconds=0,
        )

        records = provider.discover(max_results=5)

        self.assertEqual(len(records), 1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(records[0].source_id, "arxiv:2605.12345v2")

    def test_arxiv_provider_does_not_retry_http_rate_limit_errors(self) -> None:
        research_sources, _, _ = self._modules()
        calls = []
        headers = Message()
        headers["Retry-After"] = "120"

        def rate_limited_fetch(url: str) -> str:
            calls.append(url)
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", hdrs=headers, fp=None)

        provider = research_sources.ArxivProvider(
            ["cs.CL"],
            fetch_text=rate_limited_fetch,
            request_delay_seconds=0,
            retry_attempts=3,
            retry_delay_seconds=0,
        )

        with self.assertRaisesRegex(
            research_sources.ResearchProviderError,
            "arxiv provider rate limited.*Retry-After: 120",
        ):
            provider.discover(max_results=5)

        self.assertEqual(len(calls), 1)

    def test_configured_url_provider_returns_metadata_page(self) -> None:
        research_sources, _, _ = self._modules()
        html = """<html>
<head><title>Research Updates</title></head>
<body><main><p>Agent framework release</p></main></body>
</html>
"""

        provider = research_sources.ConfiguredUrlProvider(
            ["https://example.com/research"],
            fetch_text=lambda _url: html,
        )

        records = provider.discover(max_results=10)

        self.assertEqual(len(records), 1)
        source = records[0]
        self.assertEqual(source.provider, "configured-url")
        self.assertEqual(source.title, "Research Updates")
        self.assertIn("Agent framework release", source.text_preview)

    def test_openreview_provider_parses_notes_response(self) -> None:
        research_sources, _, _ = self._modules()
        response = json.dumps(
            {
                "notes": [
                    {
                        "id": "abc123",
                        "forum": "abc123",
                        "invitation": "ICLR.cc/2026/Conference/-/Submission",
                        "cdate": 1777075200000,
                        "tmdate": 1777161600000,
                        "content": {
                            "title": {"value": "Agent Review Paper"},
                            "abstract": {"value": "A review about agent frameworks."},
                        },
                    }
                ]
            }
        )

        provider = research_sources.OpenReviewProvider(
            ["ICLR.cc/2026/Conference/-/Submission"],
            fetch_text=lambda _url: response,
        )

        records = provider.discover(max_results=5)

        self.assertEqual(len(records), 1)
        source = records[0]
        self.assertEqual(source.provider, "openreview")
        self.assertEqual(source.metadata["openreview_id"], "abc123")
        self.assertEqual(source.metadata["forum"], "abc123")
        self.assertEqual(source.title, "Agent Review Paper")

    def test_openreview_provider_rejects_response_without_notes_list(self) -> None:
        research_sources, _, _ = self._modules()
        provider = research_sources.OpenReviewProvider(
            ["ICLR.cc/2026/Conference/-/Submission"],
            fetch_text=lambda _url: json.dumps({"status": "ok"}),
        )

        with self.assertRaisesRegex(research_sources.ResearchProviderError, "OpenReview|notes"):
            provider.discover(max_results=5)

    def test_openreview_provider_rejects_non_object_notes(self) -> None:
        research_sources, _, _ = self._modules()
        provider = research_sources.OpenReviewProvider(
            ["ICLR.cc/2026/Conference/-/Submission"],
            fetch_text=lambda _url: json.dumps({"notes": ["not-a-note"]}),
        )

        with self.assertRaisesRegex(research_sources.ResearchProviderError, "OpenReview|notes"):
            provider.discover(max_results=5)

    def test_openreview_provider_rejects_note_without_id(self) -> None:
        research_sources, _, _ = self._modules()
        provider = research_sources.OpenReviewProvider(
            ["ICLR.cc/2026/Conference/-/Submission"],
            fetch_text=lambda _url: json.dumps({"notes": [{}]}),
        )

        with self.assertRaisesRegex(research_sources.ResearchProviderError, "OpenReview|id"):
            provider.discover(max_results=5)

    def test_openreview_provider_rejects_invalid_forum_when_present(self) -> None:
        research_sources, _, _ = self._modules()
        for forum in ("", 123):
            with self.subTest(forum=forum):
                provider = research_sources.OpenReviewProvider(
                    ["ICLR.cc/2026/Conference/-/Submission"],
                    fetch_text=lambda _url, forum=forum: json.dumps(
                        {"notes": [{"id": "abc123", "forum": forum}]}
                    ),
                )

                with self.assertRaisesRegex(research_sources.ResearchProviderError, "OpenReview|forum"):
                    provider.discover(max_results=5)

    def test_openreview_provider_rejects_malformed_json(self) -> None:
        research_sources, _, _ = self._modules()
        provider = research_sources.OpenReviewProvider(
            ["ICLR.cc/2026/Conference/-/Submission"],
            fetch_text=lambda _url: "{not json",
        )

        with self.assertRaisesRegex(research_sources.ResearchProviderError, "OpenReview|JSON"):
            provider.discover(max_results=5)


if __name__ == "__main__":
    unittest.main()
