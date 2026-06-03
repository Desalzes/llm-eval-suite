import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.improve_set import _build_decision, _write_diagnosis, run_improve_set


ROOT = Path(__file__).resolve().parents[1]


class ImproveSetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="improve-set-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_eval_set(self) -> Path:
        set_path = self.temp_dir / "core.json"
        set_path.write_text(
            json.dumps(
                {
                    "id": "core",
                    "name": "Core Eval Set",
                    "description": "One deterministic smoke task.",
                    "tasks": [
                        {
                            "path": "tasks/examples/python-cli-bugfix/task.json",
                            "weight": 1,
                            "tags": ["smoke", "bugfix"],
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return set_path

    def _write_fixer_profile(self) -> Path:
        profile_path = self.temp_dir / "fixer.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": "fixer",
                    "name": "Fixer",
                    "description": "Fixes the calculator task.",
                    "command": [
                        sys.executable,
                        "-c",
                        (
                            "from pathlib import Path; "
                            "p=Path('calculator.py'); "
                            "text=p.read_text(encoding='utf-8'); "
                            "p.write_text(text.replace("
                            "'def subtract(left: int, right: int) -> int:\\n    return left + right', "
                            "'def subtract(left: int, right: int) -> int:\\n    return left - right'"
                            "), encoding='utf-8')"
                        ),
                    ],
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def _write_noop_profile(self) -> Path:
        profile_path = self.temp_dir / "noop.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": "noop",
                    "name": "Noop",
                    "description": "Prints the prompt and makes no edits.",
                    "command": [
                        sys.executable,
                        "-c",
                        "import pathlib, sys; print(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')[:80])",
                        "{prompt_file}",
                    ],
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def test_improve_set_marks_passing_eval_set_as_keep(self) -> None:
        summary = run_improve_set(
            suite_root=ROOT,
            set_path=self._write_eval_set(),
            profile_path=self._write_fixer_profile(),
            run_id="unit-improve-set-keep",
            improvement_runs_dir=self.temp_dir / "improvement-runs",
            eval_runs_dir=self.temp_dir / "eval-runs",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        cycle_dir = Path(summary["cycle_dir"])

        self.assertEqual(summary["decision"]["status"], "keep")
        self.assertEqual(summary["baseline_summary"]["status"], "passed")
        self.assertTrue((cycle_dir / "objective.md").exists())
        self.assertTrue((cycle_dir / "baseline-summary.json").exists())
        self.assertTrue((cycle_dir / "diagnosis.md").exists())
        self.assertTrue((cycle_dir / "proposed-change.md").exists())
        self.assertTrue((cycle_dir / "decision.md").exists())
        self.assertTrue((cycle_dir / "retained-lessons.md").exists())
        self.assertTrue((cycle_dir / "summary.json").exists())

    def test_improve_set_diagnoses_failed_eval_set(self) -> None:
        summary = run_improve_set(
            suite_root=ROOT,
            set_path=self._write_eval_set(),
            profile_path=self._write_noop_profile(),
            run_id="unit-improve-set-failed",
            improvement_runs_dir=self.temp_dir / "improvement-runs",
            eval_runs_dir=self.temp_dir / "eval-runs",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        cycle_dir = Path(summary["cycle_dir"])
        diagnosis = (cycle_dir / "diagnosis.md").read_text(encoding="utf-8")
        proposed = (cycle_dir / "proposed-change.md").read_text(encoding="utf-8")
        finding = json.loads((cycle_dir / "findings.jsonl").read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(summary["decision"]["status"], "needs_improvement")
        self.assertEqual(summary["findings"], [finding])
        self.assertEqual(finding["detector_id"], "suite.improve_set")
        self.assertEqual(finding["artifact_id"], "unit-improve-set-failed")
        self.assertEqual(finding["finding_type"], "eval_set_needs_improvement")
        self.assertEqual(finding["severity"], "medium")
        self.assertEqual(finding["confidence"], "high")
        self.assertEqual(finding["required_approval_tier"], "human_review")
        self.assertIn("failed: 1", diagnosis)
        self.assertIn("tests still failed", diagnosis)
        self.assertIn("Inspect failed run artifacts", proposed)

    def test_improve_set_diagnoses_timeout_after_validation_passed(self) -> None:
        run_dir = self.temp_dir / "run"
        run_dir.mkdir()
        (run_dir / "result.json").write_text(
            json.dumps(
                {
                    "child_status": "timeout",
                    "changed_files": ["calculator.py"],
                    "forbidden_changed_files": [],
                    "tests_passed": True,
                    "child_trace": {"tool_call_count": 11, "mentions_tests": True, "mentions_skills": True},
                }
            ),
            encoding="utf-8",
        )
        baseline_summary = {
            "status_counts": {"failed": 1},
            "runs": [
                {
                    "task_id": "python-cli-bugfix",
                    "status": "failed",
                    "run_dir": str(run_dir),
                }
            ],
        }

        decision = _build_decision(baseline_summary)
        diagnosis_path = self.temp_dir / "diagnosis.md"
        _write_diagnosis(diagnosis_path, baseline_summary)
        diagnosis = diagnosis_path.read_text(encoding="utf-8")

        self.assertEqual(decision["status"], "needs_improvement")
        self.assertIn("timed out after validation passed", decision["reason"])
        self.assertIn("validation passed but child timed out", diagnosis)

    def test_improve_set_cli_runs_cycle(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "improve-set",
                "--set",
                str(self._write_eval_set()),
                "--profile",
                str(self._write_fixer_profile()),
                "--run-id",
                "cli-improve-set",
                "--improvement-runs-dir",
                str(self.temp_dir / "improvement-runs"),
                "--eval-runs-dir",
                str(self.temp_dir / "eval-runs"),
                "--timeout-seconds",
                "5",
                "--idle-timeout-seconds",
                "5",
                "--max-output-bytes",
                "4096",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("[improve-set] starting cli-improve-set", completed.stderr)
        self.assertIn("[improve-set] cli-improve-set -> keep", completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["decision"]["status"], "keep")


if __name__ == "__main__":
    unittest.main()
