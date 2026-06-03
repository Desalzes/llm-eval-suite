import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.findings import summarize_findings


ROOT = Path(__file__).resolve().parents[1]


def _finding(
    finding_id: str,
    finding_type: str,
    severity: str,
    approval: str,
    detector_id: str = "unit.detector",
) -> dict:
    return {
        "schema_version": "finding_v1",
        "finding_id": finding_id,
        "detector_id": detector_id,
        "artifact_id": f"artifact-{finding_id}",
        "finding_type": finding_type,
        "severity": severity,
        "confidence": "high",
        "summary": f"{finding_type} summary",
        "affected_artifacts": [f"artifact-{finding_id}.json"],
        "provenance": {"source": "unit"},
        "suggested_fix": "Inspect the artifact.",
        "required_approval_tier": approval,
        "details": {},
    }


class FindingsTests(unittest.TestCase):
    def test_summarize_findings_counts_and_prioritizes_records(self) -> None:
        with tempfile.TemporaryDirectory(prefix="findings-summary-test-") as temp_dir:
            root = Path(temp_dir)
            first = root / "runs" / "one" / "findings.jsonl"
            second = root / "improvement-runs" / "two" / "findings.jsonl"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text(
                json.dumps(_finding("1", "tests_failed", "medium", "human_review")) + "\n"
                + json.dumps(_finding("2", "eval_set_clean", "info", "none")) + "\n",
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(_finding("3", "unsafe_edit", "high", "admin_review", "suite.inspect_run")) + "\n",
                encoding="utf-8",
            )

            summary = summarize_findings(root)

        self.assertEqual(summary["status"], "attention")
        self.assertEqual(summary["finding_count"], 3)
        self.assertEqual(summary["files_scanned"], 2)
        self.assertEqual(summary["by_severity"], {"high": 1, "info": 1, "medium": 1})
        self.assertEqual(summary["by_type"], {"eval_set_clean": 1, "tests_failed": 1, "unsafe_edit": 1})
        self.assertEqual(summary["by_detector"], {"suite.inspect_run": 1, "unit.detector": 2})
        self.assertEqual(summary["requires_approval"], {"admin_review": 1, "human_review": 1, "none": 1})
        self.assertEqual(summary["top_findings"][0]["finding_type"], "unsafe_edit")
        self.assertEqual(summary["top_findings"][0]["severity"], "high")

    def test_summarize_findings_cli_prints_json_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="findings-cli-test-") as temp_dir:
            root = Path(temp_dir)
            findings_path = root / "runs" / "one" / "findings.jsonl"
            findings_path.parent.mkdir(parents=True)
            findings_path.write_text(
                json.dumps(_finding("1", "tests_failed", "medium", "human_review")) + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "suite.cli",
                    "summarize-findings",
                    "--root",
                    str(root),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

        self.assertEqual(completed.returncode, 1, completed.stderr + completed.stdout)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "attention")
        self.assertEqual(summary["finding_count"], 1)
        self.assertEqual(summary["top_findings"][0]["required_approval_tier"], "human_review")


if __name__ == "__main__":
    unittest.main()
