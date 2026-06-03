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


class PolymarketHypothesesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="polymarket-hypotheses-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _snapshot_payload(self) -> dict:
        return {
            "schema_version": "polymarket_market_snapshots_v1",
            "snapshots": [
                {
                    "schema_version": "polymarket_market_snapshot_v1",
                    "snapshot_id": "snap-fed-june",
                    "captured_at": "2026-05-20T00:17:02Z",
                    "source": "polymarket-gamma-events",
                    "source_url": "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=1",
                    "market_id": "mkt-1",
                    "event_slug": "fed-decision-in-june",
                    "question": "Will the Fed cut rates in June?",
                    "outcomes": ["Yes", "No"],
                    "prices": {"Yes": 0.42, "No": 0.58},
                    "orderbook": {},
                    "volume": 12000.0,
                    "liquidity": 4000.0,
                    "end_date": "2026-06-18T00:00:00Z",
                    "closed": False,
                    "resolution_status": "open",
                    "raw_artifact": {"event_id": "evt-1", "market_condition_id": "cond-1"},
                }
            ],
        }

    def test_build_hypothesis_cards_from_snapshots_are_paper_only_and_schema_valid(self) -> None:
        from suite.contracts import validate_contract
        from suite.polymarket_hypotheses import build_hypothesis_cards

        cards = build_hypothesis_cards(
            self._snapshot_payload()["snapshots"],
            created_at="2026-05-20T00:53:03Z",
            agent_profile_id="deterministic-public-snapshot-seeder",
            model="none",
            max_cards=1,
        )

        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(validate_contract("polymarket-hypothesis", card), [])
        self.assertEqual(card["market_id"], "mkt-1")
        self.assertEqual(card["source_snapshot_id"], "snap-fed-june")
        self.assertTrue(card["paper_only"])
        self.assertEqual(card["expected_edge"], "unproven")
        self.assertIn("No live orders", card["entry_rule"])
        self.assertIn("falsified", card["falsification_rule"])

    def test_run_polymarket_hypotheses_writes_reviewable_artifacts(self) -> None:
        from suite.polymarket_hypotheses import run_polymarket_hypotheses

        snapshots_path = self.temp_dir / "market-snapshots.json"
        snapshots_path.write_text(json.dumps(self._snapshot_payload()), encoding="utf-8")

        summary = run_polymarket_hypotheses(
            suite_root=self.temp_dir,
            snapshots_path=snapshots_path,
            run_id="unit-hypotheses",
            max_cards=1,
            force=True,
        )

        run_dir = self.temp_dir / "polymarket-runs" / "unit-hypotheses"
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["mode"], "polymarket-hypotheses")
        self.assertEqual(summary["hypothesis_count"], 1)
        self.assertEqual(summary["data_access"], "public-only")
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "hypotheses" / "hypothesis-cards.json").exists())
        self.assertTrue((run_dir / "summary.json").exists())
        self.assertTrue((run_dir / "summary.md").exists())
        payload = json.loads((run_dir / "hypotheses" / "hypothesis-cards.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["hypotheses"][0]["paper_only"])

    def test_polymarket_hypotheses_cli_writes_json_summary(self) -> None:
        snapshots_path = self.temp_dir / "market-snapshots.json"
        snapshots_path.write_text(json.dumps(self._snapshot_payload()), encoding="utf-8")
        runs_dir = self.temp_dir / "polymarket-runs"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "polymarket-hypotheses",
                "--snapshots",
                str(snapshots_path),
                "--run-id",
                "cli-hypotheses",
                "--runs-dir",
                str(runs_dir),
                "--max-cards",
                "1",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["mode"], "polymarket-hypotheses")
        self.assertEqual(summary["hypothesis_count"], 1)
        self.assertTrue((runs_dir / "cli-hypotheses" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
