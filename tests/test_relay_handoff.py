import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class RelayHandoffTests(unittest.TestCase):
    def _sample_handoff(self) -> dict:
        return {
            "schema_version": "relay_handoff_v1",
            "session_id": "ms-weather-local-smoke",
            "scope": "WEATHER",
            "scope_marker": "MASTER: WEATHER",
            "project": "Weather Betting Markets",
            "hard_rules": [
                "Start user-visible responses with MASTER: WEATHER.",
                "Keep .claude read-only unless explicitly scoped.",
            ],
            "source_boundaries": [
                "Root suite source is C:/Users/desal/ChatGPT.",
                "Project pack source is read-only unless an implementation session is opened.",
            ],
            "changed_files": [
                "suite/master_session.py",
                "schemas/orientation.schema.json",
            ],
            "generated_artifacts": [
                "runs/master-sessions/ms-weather-local-smoke/orientation.json",
                "runs/master-sessions/ms-weather-local-smoke/handoff.json",
            ],
            "unresolved_risks": [
                "Project-pack handoff notes are optional and may be absent.",
            ],
            "next_action": "Define relay handoff lab fixtures.",
            "verification_evidence": [
                "python -m unittest discover -s tests -> 177 passed",
                "git diff --check -> exit 0",
            ],
            "project_pack_authority_reads": [
                {
                    "source": "project_pack",
                    "path": "AGENTS.md",
                    "status": "present",
                    "required": True,
                },
                {
                    "source": "project_pack",
                    "path": "docs/session-handoff.md",
                    "status": "missing",
                    "required": False,
                },
            ],
        }

    def test_relay_handoff_schema_is_registered(self) -> None:
        from suite.contracts import validate_contract

        self.assertEqual(validate_contract("relay-handoff", self._sample_handoff()), [])

    def test_formatters_preserve_required_relay_fields(self) -> None:
        from suite.relay_handoff import (
            format_compact_json,
            format_json,
            format_markdown,
            format_toon,
            score_relay_handoff_text,
        )

        handoff = self._sample_handoff()
        rendered = {
            "json": format_json(handoff),
            "compact_json": format_compact_json(handoff),
            "markdown": format_markdown(handoff),
            "toon": format_toon(handoff),
        }

        self.assertLess(len(rendered["compact_json"]), len(rendered["json"]))
        for name, text in rendered.items():
            with self.subTest(format=name):
                score = score_relay_handoff_text(text)
                self.assertEqual(score["overall"], "pass")
                self.assertEqual(score["passed"], score["total"])
                value_score = score_relay_handoff_text(text, expected=handoff)
                self.assertEqual(value_score["overall"], "pass")
                self.assertEqual(value_score["passed"], value_score["total"])

    def test_scorer_reports_missing_required_relay_fields(self) -> None:
        from suite.relay_handoff import score_relay_handoff_text

        score = score_relay_handoff_text("scope: WEATHER\nnext_action: Continue.\n")

        self.assertEqual(score["overall"], "fail")
        failed = {item["name"] for item in score["checks"] if item["status"] == "fail"}
        self.assertIn("hard_rules", failed)
        self.assertIn("verification_evidence", failed)
        self.assertIn("project_pack_authority_reads", failed)

    def test_scorer_reports_missing_expected_relay_values(self) -> None:
        from suite.relay_handoff import score_relay_handoff_text

        text = """# Relay Handoff: WEATHER

scope_marker: MASTER: WEATHER

## Hard Rules
- hard rule omitted

## Source Boundaries
- source boundary omitted

## Changed Files
- changed file omitted

## Unresolved Risks
- risk omitted

## Next Action
next action omitted

## Verification Evidence
- verification evidence omitted

## Project Pack Authority Reads
- project pack read omitted
"""

        score = score_relay_handoff_text(text, expected=self._sample_handoff())

        failed = {item["name"] for item in score["checks"] if item["status"] == "fail"}
        self.assertEqual(score["overall"], "fail")
        self.assertIn("hard_rules_values", failed)
        self.assertIn("changed_files_values", failed)
        self.assertIn("verification_evidence_values", failed)
        self.assertIn("project_pack_authority_reads_values", failed)

    def test_json_formatter_outputs_parseable_schema_instance(self) -> None:
        from suite.contracts import validate_contract
        from suite.relay_handoff import format_json

        parsed = json.loads(format_json(self._sample_handoff()))

        self.assertEqual(validate_contract("relay-handoff", parsed), [])

    def test_token_count_summary_uses_tiktoken_when_available(self) -> None:
        from suite.relay_handoff import token_count_summary

        class FakeEncoding:
            def encode(self, text: str) -> list[str]:
                return text.split()

        class FakeTiktoken:
            def get_encoding(self, name: str) -> FakeEncoding:
                self.name = name
                return FakeEncoding()

        fake_tiktoken = FakeTiktoken()

        with patch.dict(sys.modules, {"tiktoken": fake_tiktoken}):
            summary = token_count_summary("one two three")

        self.assertEqual(fake_tiktoken.name, "o200k_base")
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["method"], "tiktoken:o200k_base")

    def test_relay_fixture_files_validate_and_score(self) -> None:
        from suite.contracts import validate_contract
        from suite.relay_handoff import (
            format_compact_json,
            format_json,
            format_markdown,
            format_toon,
            score_relay_handoff_text,
        )

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff = json.loads((fixture_dir / "relay-handoff.json").read_text(encoding="utf-8"))
        lossy_text = (fixture_dir / "lossy-summary.md").read_text(encoding="utf-8")

        self.assertEqual(validate_contract("relay-handoff", handoff), [])
        for formatter in [format_json, format_compact_json, format_markdown, format_toon]:
            score = score_relay_handoff_text(formatter(handoff), expected=handoff)
            self.assertEqual(score["overall"], "pass")

        lossy_score = score_relay_handoff_text(lossy_text, expected=handoff)
        failed = {item["name"] for item in lossy_score["checks"] if item["status"] == "fail"}
        self.assertEqual(lossy_score["overall"], "fail")
        self.assertIn("changed_files_values", failed)
        self.assertIn("verification_evidence_values", failed)

    def test_render_relay_handoff_run_writes_formats_and_scores(self) -> None:
        from suite.relay_handoff import render_relay_handoff_run

        handoff_path = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped" / "relay-handoff.json"
        with tempfile.TemporaryDirectory(prefix="relay-render-test-") as temp_dir:
            output_dir = Path(temp_dir) / "rendered"

            summary = render_relay_handoff_run(handoff_path, output_dir)

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["overall"], "pass")
            self.assertEqual(set(summary["formats"]), {"json", "compact_json", "markdown", "toon"})
            self.assertEqual(summary["best_by_estimated_tokens"], "markdown")
            self.assertTrue((output_dir / "formats" / "handoff.json").exists())
            self.assertTrue((output_dir / "formats" / "handoff.compact.json").exists())
            self.assertTrue((output_dir / "formats" / "handoff.md").exists())
            self.assertTrue((output_dir / "formats" / "handoff.toon").exists())
            scores = json.loads((output_dir / "scores.json").read_text(encoding="utf-8"))
            self.assertEqual({name: item["overall"] for name, item in scores["scores"].items()}, {
                "json": "pass",
                "compact_json": "pass",
                "markdown": "pass",
                "toon": "pass",
            })
            for format_summary in summary["formats"].values():
                self.assertGreater(format_summary["estimated_tokens"], 0)
                self.assertGreater(format_summary["tokens"]["count"], 0)
                self.assertIn("method", format_summary["tokens"])
            comparison = (output_dir / "comparison.md").read_text(encoding="utf-8")
            self.assertIn("| Format | Bytes | Estimated Tokens | Token Count | Token Method | Score |", comparison)
            self.assertIn("| compact_json |", comparison)
            self.assertTrue((output_dir / "summary.json").exists())

    def test_relay_handoff_render_cli_writes_json_summary(self) -> None:
        handoff_path = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped" / "relay-handoff.json"
        with tempfile.TemporaryDirectory(prefix="relay-render-cli-test-") as temp_dir:
            output_dir = Path(temp_dir) / "rendered"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "suite.cli",
                    "relay-handoff-render",
                    "--handoff",
                    str(handoff_path),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(completed.stdout)
            self.assertEqual(summary["overall"], "pass")
            self.assertTrue((output_dir / "summary.json").exists())

    def test_write_relay_prompt_pack_writes_prompt_files(self) -> None:
        from suite.relay_handoff import write_relay_prompt_pack

        handoff_path = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped" / "relay-handoff.json"
        with tempfile.TemporaryDirectory(prefix="relay-prompts-test-") as temp_dir:
            output_dir = Path(temp_dir) / "prompts"

            summary = write_relay_prompt_pack(handoff_path, output_dir)

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(set(summary["prompts"]), {"json", "compact_json", "markdown", "toon"})
            json_prompt = Path(summary["prompts"]["json"]["artifact"]).read_text(encoding="utf-8")
            toon_prompt = Path(summary["prompts"]["toon"]["artifact"]).read_text(encoding="utf-8")
            self.assertIn("Return one JSON object", json_prompt)
            self.assertIn("relay_handoff_v1", json_prompt)
            self.assertIn("MASTER: WEATHER", toon_prompt)
            self.assertGreater(summary["prompts"]["json"]["tokens"]["count"], 0)
            self.assertIn("method", summary["prompts"]["json"]["tokens"])
            self.assertTrue((output_dir / "summary.json").exists())

    def test_relay_handoff_prompts_cli_writes_json_summary(self) -> None:
        handoff_path = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped" / "relay-handoff.json"
        with tempfile.TemporaryDirectory(prefix="relay-prompts-cli-test-") as temp_dir:
            output_dir = Path(temp_dir) / "prompts"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "suite.cli",
                    "relay-handoff-prompts",
                    "--handoff",
                    str(handoff_path),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(completed.stdout)
            self.assertEqual(set(summary["prompts"]), {"json", "compact_json", "markdown", "toon"})
            self.assertTrue((output_dir / "summary.json").exists())

    def test_score_relay_handoff_received_passes_and_fails(self) -> None:
        from suite.relay_handoff import format_markdown, score_relay_handoff_received

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-test-") as temp_dir:
            received_path = Path(temp_dir) / "received.md"
            received_path.write_text(format_markdown(handoff), encoding="utf-8")

            passing = score_relay_handoff_received(handoff_path, received_path)
            failing = score_relay_handoff_received(handoff_path, fixture_dir / "lossy-summary.md")

            self.assertEqual(passing["overall"], "pass")
            self.assertEqual(passing["passed"], passing["total"])
            self.assertEqual(failing["overall"], "fail")

    def test_score_relay_handoff_received_reports_json_parse_status(self) -> None:
        from suite.relay_handoff import format_compact_json, score_relay_handoff_received

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-json-test-") as temp_dir:
            received_path = Path(temp_dir) / "received.json"
            received_path.write_text(format_compact_json(handoff), encoding="utf-8")

            score = score_relay_handoff_received(handoff_path, received_path)

            self.assertEqual(score["overall"], "pass")
            self.assertEqual(score["received_json_status"], "valid")
            self.assertEqual(score["received_json_contract"], "pass")

    def test_score_relay_handoff_received_dir_summarizes_multiple_outputs(self) -> None:
        from suite.relay_handoff import format_markdown, score_relay_handoff_received_dir

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-dir-test-") as temp_dir:
            temp_path = Path(temp_dir)
            received_dir = temp_path / "received"
            output_dir = temp_path / "scores"
            received_dir.mkdir()
            (received_dir / "passing.md").write_text(format_markdown(handoff), encoding="utf-8")
            (received_dir / "lossy.md").write_text(
                (fixture_dir / "lossy-summary.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            summary = score_relay_handoff_received_dir(handoff_path, received_dir, output_dir)

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["mode"], "relay-handoff-score-dir")
            self.assertEqual(summary["overall"], "fail")
            self.assertEqual(summary["received_count"], 2)
            self.assertEqual(summary["pass_count"], 1)
            self.assertEqual(summary["fail_count"], 1)
            self.assertEqual([item["name"] for item in summary["received"]], ["lossy.md", "passing.md"])
            self.assertGreater(summary["received"][0]["tokens"]["count"], 0)
            self.assertIn("method", summary["received"][0]["tokens"])
            self.assertTrue((output_dir / "scores" / "lossy.md.json").exists())
            self.assertTrue((output_dir / "scores" / "passing.md.json").exists())
            self.assertTrue((output_dir / "summary.json").exists())
            self.assertTrue((output_dir / "comparison.md").exists())

    def test_score_relay_handoff_received_dir_includes_model_metadata(self) -> None:
        from suite.relay_handoff import format_json, score_relay_handoff_received_dir

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-dir-metadata-test-") as temp_dir:
            temp_path = Path(temp_dir)
            received_dir = temp_path / "received"
            output_dir = temp_path / "scores"
            metadata_path = temp_path / "metadata.json"
            received_dir.mkdir()
            (received_dir / "received.json").write_text(format_json(handoff), encoding="utf-8")
            metadata_path.write_text(
                json.dumps(
                    {
                        "schema_version": "relay_received_metadata_v1",
                        "run_id": "manual-weather-001",
                        "captured_at": "2026-05-19T20:09:11Z",
                        "outputs": [
                            {
                                "file": "received.json",
                                "format": "json",
                                "provider": "openai",
                                "model": "gpt-5.4",
                                "session_id": "root-master",
                                "prompt_file": "prompt-json.md",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            summary = score_relay_handoff_received_dir(handoff_path, received_dir, output_dir, metadata_path=metadata_path)

            self.assertEqual(summary["metadata"]["run_id"], "manual-weather-001")
            self.assertEqual(summary["metadata"]["captured_at"], "2026-05-19T20:09:11Z")
            self.assertEqual(summary["received"][0]["metadata"]["provider"], "openai")
            self.assertEqual(summary["received"][0]["metadata"]["model"], "gpt-5.4")
            comparison = (output_dir / "comparison.md").read_text(encoding="utf-8")
            self.assertIn("openai", comparison)
            self.assertIn("gpt-5.4", comparison)

    def test_score_relay_handoff_received_dir_ignores_metadata_sidecar_in_received_dir(self) -> None:
        from suite.relay_handoff import format_json, score_relay_handoff_received_dir

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-dir-sidecar-test-") as temp_dir:
            temp_path = Path(temp_dir)
            received_dir = temp_path / "received"
            output_dir = temp_path / "scores"
            metadata_path = received_dir / "metadata.json"
            received_dir.mkdir()
            (received_dir / "received.json").write_text(format_json(handoff), encoding="utf-8")
            metadata_path.write_text(
                json.dumps(
                    {
                        "schema_version": "relay_received_metadata_v1",
                        "run_id": "sidecar-smoke",
                        "outputs": [{"file": "received.json", "provider": "local", "model": "formatter-smoke"}],
                    }
                ),
                encoding="utf-8",
            )

            summary = score_relay_handoff_received_dir(handoff_path, received_dir, output_dir, metadata_path=metadata_path)

            self.assertEqual(summary["overall"], "pass")
            self.assertEqual(summary["received_count"], 1)
            self.assertEqual(summary["received"][0]["name"], "received.json")

    def test_relay_handoff_score_cli_writes_json_summary(self) -> None:
        from suite.relay_handoff import format_json

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-cli-test-") as temp_dir:
            received_path = Path(temp_dir) / "received.json"
            output_path = Path(temp_dir) / "score.json"
            received_path.write_text(format_json(handoff), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "suite.cli",
                    "relay-handoff-score",
                    "--expected",
                    str(handoff_path),
                    "--received",
                    str(received_path),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(completed.stdout)
            self.assertEqual(summary["overall"], "pass")
            self.assertTrue(output_path.exists())

    def test_relay_handoff_score_dir_cli_writes_json_summary(self) -> None:
        from suite.relay_handoff import format_json

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-dir-cli-test-") as temp_dir:
            temp_path = Path(temp_dir)
            received_dir = temp_path / "received"
            output_dir = temp_path / "scores"
            received_dir.mkdir()
            (received_dir / "received.json").write_text(format_json(handoff), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "suite.cli",
                    "relay-handoff-score-dir",
                    "--expected",
                    str(handoff_path),
                    "--received-dir",
                    str(received_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(completed.stdout)
            self.assertEqual(summary["overall"], "pass")
            self.assertEqual(summary["received_count"], 1)
            self.assertTrue((output_dir / "summary.json").exists())

    def test_relay_handoff_score_dir_cli_accepts_metadata(self) -> None:
        from suite.relay_handoff import format_json

        fixture_dir = ROOT / "tasks" / "relay-handoff-fixtures" / "weather-scoped"
        handoff_path = fixture_dir / "relay-handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="relay-score-dir-cli-metadata-test-") as temp_dir:
            temp_path = Path(temp_dir)
            received_dir = temp_path / "received"
            output_dir = temp_path / "scores"
            metadata_path = temp_path / "metadata.json"
            received_dir.mkdir()
            (received_dir / "received.json").write_text(format_json(handoff), encoding="utf-8")
            metadata_path.write_text(
                json.dumps(
                    {
                        "schema_version": "relay_received_metadata_v1",
                        "run_id": "cli-manual-weather-001",
                        "outputs": [
                            {
                                "file": "received.json",
                                "provider": "anthropic",
                                "model": "claude-sonnet-4.5",
                                "format": "json",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "suite.cli",
                    "relay-handoff-score-dir",
                    "--expected",
                    str(handoff_path),
                    "--received-dir",
                    str(received_dir),
                    "--output-dir",
                    str(output_dir),
                    "--metadata",
                    str(metadata_path),
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(completed.stdout)
            self.assertEqual(summary["metadata"]["run_id"], "cli-manual-weather-001")
            self.assertEqual(summary["received"][0]["metadata"]["provider"], "anthropic")


if __name__ == "__main__":
    unittest.main()
