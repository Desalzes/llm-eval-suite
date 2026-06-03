import json
import tempfile
import unittest
from pathlib import Path


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class InnovationCompareTests(unittest.TestCase):
    def test_summarizes_innovation_run_from_result_and_plan(self) -> None:
        from suite.innovation_compare import summarize_innovation_run

        with tempfile.TemporaryDirectory(prefix="innovation-compare-test-") as temp:
            run_dir = Path(temp) / "skill-run"
            _write_json(
                run_dir / "result.json",
                {
                    "run_id": "skill-run",
                    "status": "passed",
                    "tests_passed": True,
                    "child_trace": {
                        "skill_file_read_count": 1,
                        "tokens_used": 1234,
                        "tool_call_count": 7,
                    },
                },
            )
            _write_json(
                run_dir / "workspace" / "innovation_plan.json",
                {
                    "branches": [{"name": "a"}, {"name": "b"}],
                    "remote_analogies": [{"source_domain": "coding theory"}],
                    "representation_shifts": [{"to": "incidence vector"}],
                    "construction_search": {"candidate_family": "gadgets"},
                    "certificate_plan": {"checker": "pytest", "falsification_tests": ["seed"]},
                },
            )
            (run_dir / "child").mkdir()
            (run_dir / "child" / "transcript.txt").write_text(
                "read C:/Users/desal/.codex/skills/branching-innovation/SKILL.md",
                encoding="utf-8",
            )

            summary = summarize_innovation_run(run_dir, label="skill")

        self.assertEqual(summary["label"], "skill")
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["branch_count"], 2)
        self.assertEqual(summary["remote_analogy_count"], 1)
        self.assertEqual(summary["representation_shift_count"], 1)
        self.assertTrue(summary["has_construction_search"])
        self.assertTrue(summary["has_certificate_plan"])
        self.assertTrue(summary["branching_innovation_used"])
        self.assertEqual(summary["skill_file_read_count"], 1)
        self.assertEqual(summary["tokens_used"], 1234)

    def test_writes_markdown_report_for_labeled_runs(self) -> None:
        from suite.innovation_compare import write_comparison_report

        with tempfile.TemporaryDirectory(prefix="innovation-report-test-") as temp:
            root = Path(temp)
            for label, skill_reads in [("control", 0), ("skill", 1)]:
                run_dir = root / label
                _write_json(
                    run_dir / "result.json",
                    {
                        "run_id": label,
                        "status": "passed",
                        "tests_passed": True,
                        "child_trace": {
                            "skill_file_read_count": skill_reads,
                            "tokens_used": 100 + skill_reads,
                            "tool_call_count": 4 + skill_reads,
                        },
                    },
                )
                _write_json(
                    run_dir / "workspace" / "innovation_plan.json",
                    {
                        "branches": [{"name": "a"}],
                        "remote_analogies": [],
                        "representation_shift": {"to": "conflict graph"},
                        "counterexample_families": [{"name": "gadget"}],
                        "certificate_plan": {"checker": "pytest"},
                    },
                )
                (run_dir / "child").mkdir()
                transcript = "using generic startup skill"
                if label == "skill":
                    transcript = "using branching-innovation skill"
                (run_dir / "child" / "transcript.txt").write_text(transcript, encoding="utf-8")

            output_path = root / "report.md"
            write_comparison_report(
                [
                    ("control", root / "control"),
                    ("skill", root / "skill"),
                ],
                output_path,
            )
            report = output_path.read_text(encoding="utf-8")

        self.assertIn("# Innovation A/B Comparison", report)
        self.assertIn("| control | passed | 1 | 0 | 1 | yes | yes | no | 0 | 100 | 4 |", report)
        self.assertIn("| skill | passed | 1 | 0 | 1 | yes | yes | yes | 1 | 101 | 5 |", report)
