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


class PolymarketPaperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="polymarket-paper-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _hypothesis_payload(self, *, paper_only: bool = True) -> dict:
        return {
            "schema_version": "polymarket_hypotheses_v1",
            "source_snapshots": "unit-snapshots.json",
            "hypotheses": [
                {
                    "schema_version": "polymarket_hypothesis_v1",
                    "hypothesis_id": "hyp-fed-june",
                    "created_at": "2026-05-20T00:53:03Z",
                    "agent_profile_id": "deterministic-public-snapshot-seeder",
                    "model": "none",
                    "market_scope": "fed-decision-in-june",
                    "market_id": "mkt-1",
                    "source_snapshot_id": "snap-fed-june",
                    "question": "Will the Fed cut rates in June?",
                    "outcomes": ["Yes", "No"],
                    "prices": {"Yes": 0.42, "No": 0.58},
                    "thesis": "Investigate whether public pricing is miscalibrated.",
                    "entry_rule": "No live orders. Paper simulation only.",
                    "exit_rule": "Exit when dislocation closes.",
                    "position_sizing_rule": "Cap paper exposure at 1% of paper bankroll.",
                    "data_requirements": ["fresh public Gamma market snapshot"],
                    "expected_edge": "unproven",
                    "known_risks": ["stale public data"],
                    "falsification_rule": "Falsified if paper trading fails to beat baseline.",
                    "paper_only": paper_only,
                    "claim_ids": [],
                }
            ],
        }

    def test_build_paper_trades_from_hypotheses_are_schema_valid_and_paper_only(self) -> None:
        from suite.contracts import validate_contract
        from suite.polymarket_paper import build_paper_trades

        trades = build_paper_trades(
            self._hypothesis_payload()["hypotheses"],
            opened_at="2026-05-20T01:30:00Z",
            paper_size=25.0,
            slippage=0.01,
        )

        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(validate_contract("polymarket-paper-trade", trade), [])
        self.assertTrue(trade["paper_only"])
        self.assertFalse(trade["live_trading"])
        self.assertEqual(trade["status"], "paper-open")
        self.assertEqual(trade["hypothesis_id"], "hyp-fed-june")
        self.assertEqual(trade["market_id"], "mkt-1")
        self.assertEqual(trade["side"], "buy")
        self.assertEqual(trade["outcome"], "Yes")
        self.assertEqual(trade["reference_price"], 0.42)
        self.assertEqual(trade["paper_size"], 25.0)
        self.assertEqual(trade["limit_price"], 0.43)
        self.assertEqual(trade["simulated_fill_price"], 0.43)
        self.assertEqual(trade["paper_pnl"], 0.0)
        self.assertIsNone(trade["closed_at"])
        self.assertIn("public hypothesis", trade["fill_assumption"])
        self.assertIn("No authenticated", trade["safety_notes"][0])

    def test_build_paper_trades_rejects_non_paper_hypotheses(self) -> None:
        from suite.polymarket_paper import build_paper_trades

        with self.assertRaisesRegex(ValueError, "paper_only"):
            build_paper_trades(
                self._hypothesis_payload(paper_only=False)["hypotheses"],
                opened_at="2026-05-20T01:30:00Z",
            )

    def test_run_polymarket_paper_trades_writes_reviewable_artifacts(self) -> None:
        from suite.polymarket_paper import run_polymarket_paper_trades

        hypotheses_path = self.temp_dir / "hypothesis-cards.json"
        hypotheses_path.write_text(json.dumps(self._hypothesis_payload()), encoding="utf-8")

        summary = run_polymarket_paper_trades(
            suite_root=self.temp_dir,
            hypotheses_path=hypotheses_path,
            run_id="unit-paper-trades",
            paper_size=25.0,
            slippage=0.01,
            force=True,
        )

        run_dir = self.temp_dir / "polymarket-runs" / "unit-paper-trades"
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["mode"], "polymarket-paper-trades")
        self.assertEqual(summary["data_access"], "public-only")
        self.assertFalse(summary["live_trading"])
        self.assertEqual(summary["paper_trade_count"], 1)
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "paper-trades" / "paper-trades.json").exists())
        self.assertTrue((run_dir / "summary.json").exists())
        self.assertTrue((run_dir / "summary.md").exists())
        payload = json.loads((run_dir / "paper-trades" / "paper-trades.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["paper_trades"][0]["status"], "paper-open")
        self.assertFalse(payload["paper_trades"][0]["live_trading"])

    def test_polymarket_paper_trades_cli_writes_json_summary(self) -> None:
        hypotheses_path = self.temp_dir / "hypothesis-cards.json"
        hypotheses_path.write_text(json.dumps(self._hypothesis_payload()), encoding="utf-8")
        runs_dir = self.temp_dir / "polymarket-runs"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "polymarket-paper-trades",
                "--hypotheses",
                str(hypotheses_path),
                "--run-id",
                "cli-paper-trades",
                "--runs-dir",
                str(runs_dir),
                "--paper-size",
                "25",
                "--slippage",
                "0.01",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["mode"], "polymarket-paper-trades")
        self.assertEqual(summary["paper_trade_count"], 1)
        self.assertFalse(summary["live_trading"])
        self.assertTrue((runs_dir / "cli-paper-trades" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
