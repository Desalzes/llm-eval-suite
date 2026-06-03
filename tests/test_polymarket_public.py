import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PolymarketPublicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="polymarket-public-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _gamma_events_payload(self) -> list[dict]:
        return [
            {
                "id": "evt-1",
                "slug": "fed-decision-in-june",
                "title": "Fed decision in June?",
                "volume": "12345.67",
                "liquidity": "4567.89",
                "active": True,
                "closed": False,
                "endDate": "2026-06-18T00:00:00Z",
                "markets": [
                    {
                        "id": "mkt-1",
                        "conditionId": "cond-1",
                        "slug": "fed-decision-in-june",
                        "question": "Will the Fed cut rates in June?",
                        "outcomes": "[\"Yes\", \"No\"]",
                        "outcomePrices": "[\"0.42\", \"0.58\"]",
                        "volume": "12000.00",
                        "liquidity": "4000.00",
                        "active": True,
                        "closed": False,
                        "endDate": "2026-06-18T00:00:00Z",
                    }
                ],
            }
        ]

    def test_normalize_gamma_events_writes_schema_valid_snapshots(self) -> None:
        from suite.contracts import validate_contract
        from suite.polymarket_public import normalize_gamma_events

        snapshots = normalize_gamma_events(
            self._gamma_events_payload(),
            captured_at="2026-05-20T00:17:02Z",
            source_url="https://gamma-api.polymarket.com/events?active=true&closed=false&limit=1",
            limit=1,
        )

        self.assertEqual(len(snapshots), 1)
        snapshot = snapshots[0]
        self.assertEqual(validate_contract("polymarket-market-snapshot", snapshot), [])
        self.assertEqual(snapshot["source"], "polymarket-gamma-events")
        self.assertEqual(snapshot["market_id"], "mkt-1")
        self.assertEqual(snapshot["event_slug"], "fed-decision-in-june")
        self.assertEqual(snapshot["outcomes"], ["Yes", "No"])
        self.assertEqual(snapshot["prices"], {"Yes": 0.42, "No": 0.58})
        self.assertFalse(snapshot["closed"])
        self.assertEqual(snapshot["resolution_status"], "open")

    def test_run_polymarket_snapshot_writes_public_data_artifacts(self) -> None:
        from suite.polymarket_public import run_polymarket_snapshot

        fixture_path = self.temp_dir / "gamma-events.json"
        fixture_path.write_text(json.dumps(self._gamma_events_payload()), encoding="utf-8")

        summary = run_polymarket_snapshot(
            suite_root=self.temp_dir,
            run_id="unit-snapshot",
            fixture_json=fixture_path,
            limit=1,
            force=True,
        )

        run_dir = self.temp_dir / "polymarket-runs" / "unit-snapshot"
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["mode"], "polymarket-snapshot")
        self.assertEqual(summary["market_count"], 1)
        self.assertEqual(summary["data_access"], "public-only")
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "raw" / "gamma-events.json").exists())
        self.assertTrue((run_dir / "snapshots" / "market-snapshots.json").exists())
        self.assertTrue((run_dir / "summary.md").exists())
        self.assertTrue((run_dir / "summary.json").exists())

    def test_run_polymarket_snapshot_rejects_authenticated_or_private_urls(self) -> None:
        from suite.polymarket_public import run_polymarket_snapshot

        with self.assertRaisesRegex(ValueError, "public Gamma"):
            run_polymarket_snapshot(
                suite_root=self.temp_dir,
                run_id="bad-url",
                source_url="https://clob.polymarket.com/orders",
                limit=1,
                force=True,
            )

    def test_fetch_public_gamma_uses_browser_like_headers(self) -> None:
        from suite.polymarket_public import _read_fixture_or_fetch

        captured = {}

        class FakeResponse:
            status = 200

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def read(self) -> bytes:
                return b"[]"

        def fake_urlopen(request, timeout):
            captured["user_agent"] = request.headers.get("User-agent")
            captured["accept"] = request.headers.get("Accept")
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("suite.polymarket_public.urlopen", fake_urlopen):
            payload = _read_fixture_or_fetch(None, "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=1")

        self.assertEqual(payload, [])
        self.assertIn("Mozilla", captured["user_agent"])
        self.assertEqual(captured["accept"], "application/json")
        self.assertEqual(captured["timeout"], 30)

    def test_polymarket_snapshot_cli_writes_json_summary_from_fixture(self) -> None:
        fixture_path = self.temp_dir / "gamma-events.json"
        fixture_path.write_text(json.dumps(self._gamma_events_payload()), encoding="utf-8")
        runs_dir = self.temp_dir / "polymarket-runs"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "polymarket-snapshot",
                "--run-id",
                "cli-snapshot",
                "--runs-dir",
                str(runs_dir),
                "--fixture-json",
                str(fixture_path),
                "--limit",
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
        self.assertEqual(summary["mode"], "polymarket-snapshot")
        self.assertEqual(summary["market_count"], 1)
        self.assertTrue((runs_dir / "cli-snapshot" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
