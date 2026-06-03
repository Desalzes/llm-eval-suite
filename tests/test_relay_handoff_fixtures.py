import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class RelayHandoffFixtureTests(unittest.TestCase):
    def _fixture_dirs(self) -> list[Path]:
        fixtures_root = ROOT / "tasks" / "relay-handoff-fixtures"
        return sorted(path for path in fixtures_root.iterdir() if path.is_dir())

    def test_expected_fixture_directories_are_present(self) -> None:
        fixture_names = {path.name for path in self._fixture_dirs()}

        self.assertIn("weather-scoped", fixture_names)
        self.assertIn("root-basic", fixture_names)

    def test_all_relay_handoff_fixtures_validate_and_score(self) -> None:
        from suite.contracts import validate_contract
        from suite.relay_handoff import (
            format_compact_json,
            format_json,
            format_markdown,
            format_toon,
            score_relay_handoff_text,
        )

        for fixture_dir in self._fixture_dirs():
            with self.subTest(fixture=fixture_dir.name):
                handoff_path = fixture_dir / "relay-handoff.json"
                lossy_path = fixture_dir / "lossy-summary.md"
                handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
                lossy_text = lossy_path.read_text(encoding="utf-8")

                self.assertEqual(validate_contract("relay-handoff", handoff), [])
                for formatter in [format_json, format_compact_json, format_markdown, format_toon]:
                    with self.subTest(fixture=fixture_dir.name, formatter=formatter.__name__):
                        score = score_relay_handoff_text(formatter(handoff), expected=handoff)
                        self.assertEqual(score["overall"], "pass")
                        self.assertEqual(score["passed"], score["total"])

                lossy_score = score_relay_handoff_text(lossy_text, expected=handoff)
                failed = {item["name"] for item in lossy_score["checks"] if item["status"] == "fail"}
                self.assertEqual(lossy_score["overall"], "fail")
                self.assertIn("changed_files_values", failed)
                self.assertIn("verification_evidence_values", failed)


if __name__ == "__main__":
    unittest.main()
