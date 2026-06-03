import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.improve_loop import _safe_remove_loop_dir, run_improve_set_loop


ROOT = Path(__file__).resolve().parents[1]


class ImproveLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="improve-loop-test-"))

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
                            "print('exec', flush=True); "
                            "print('tokens used\\n10', flush=True); "
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

    def test_improve_set_loop_runs_bounded_iterations(self) -> None:
        summary = run_improve_set_loop(
            suite_root=ROOT,
            set_path=self._write_eval_set(),
            profile_path=self._write_fixer_profile(),
            loop_id="unit-loop",
            max_iterations=2,
            improvement_loops_dir=self.temp_dir / "improvement-runs",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        loop_dir = Path(summary["loop_dir"])

        self.assertEqual(summary["iterations_completed"], 2)
        self.assertEqual(summary["decision_counts"], {"keep": 2})
        self.assertEqual(summary["next_action"]["kind"], "expand_eval_set")
        self.assertEqual([item["cycle_id"] for item in summary["iterations"]], ["unit-loop-01", "unit-loop-02"])
        self.assertEqual(summary["aggregate_stats"]["run_count"], 2)
        self.assertEqual(summary["aggregate_stats"]["task_count"], 1)
        self.assertEqual(summary["aggregate_stats"]["pass_count"], 2)
        self.assertEqual(summary["aggregate_stats"]["pass_rate"], 1.0)
        self.assertEqual(summary["aggregate_stats"]["total_tokens"], 20)
        self.assertEqual(summary["aggregate_stats"]["total_tool_calls"], 2)
        self.assertEqual(summary["observability"]["health"], "clean")
        self.assertEqual(summary["observability"]["token_hotspots"][0]["task_id"], "python-cli-bugfix")
        self.assertEqual(
            summary["aggregate_stats"]["per_task"]["python-cli-bugfix"]["run_count"],
            2,
        )
        self.assertEqual(
            summary["aggregate_stats"]["per_task"]["python-cli-bugfix"]["status_counts"],
            {"passed": 2},
        )
        self.assertEqual(summary["iterations"][0]["aggregate_stats"]["total_tokens"], 10)
        self.assertTrue((loop_dir / "summary.json").exists())
        self.assertTrue((loop_dir / "summary.md").exists())
        summary_md = (loop_dir / "summary.md").read_text(encoding="utf-8")
        self.assertIn("## Observability", summary_md)
        self.assertIn("Health: `clean`", summary_md)
        self.assertTrue((loop_dir / "cycles" / "unit-loop-01" / "summary.json").exists())
        self.assertTrue((loop_dir / "cycles" / "unit-loop-02" / "summary.json").exists())

    def test_improve_set_loop_requires_positive_iterations(self) -> None:
        with self.assertRaises(ValueError):
            run_improve_set_loop(
                suite_root=ROOT,
                set_path=self._write_eval_set(),
                profile_path=self._write_fixer_profile(),
                loop_id="bad-loop",
                max_iterations=0,
                improvement_loops_dir=self.temp_dir / "improvement-runs",
                force=True,
            )

    def test_safe_remove_loop_dir_handles_read_only_files(self) -> None:
        root = self.temp_dir / "loops"
        loop_dir = root / "readonly-loop"
        read_only_file = loop_dir / "workspace" / ".git" / "objects" / "readonly"
        read_only_file.parent.mkdir(parents=True)
        read_only_file.write_text("locked", encoding="utf-8")
        read_only_file.chmod(stat.S_IREAD)
        self.addCleanup(lambda: os.chmod(read_only_file, stat.S_IWRITE) if read_only_file.exists() else None)

        _safe_remove_loop_dir(loop_dir, root)

        self.assertFalse(loop_dir.exists())

    def test_improve_set_loop_cli_runs_iterations(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "improve-set-loop",
                "--set",
                str(self._write_eval_set()),
                "--profile",
                str(self._write_fixer_profile()),
                "--loop-id",
                "cli-loop",
                "--max-iterations",
                "2",
                "--improvement-loops-dir",
                str(self.temp_dir / "improvement-runs"),
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
        self.assertIn("[improve-set-loop] starting cli-loop", completed.stderr)
        self.assertIn("[improve-set-loop] cli-loop-01 -> keep", completed.stderr)
        self.assertIn("[improve-set-loop] cli-loop-02 -> keep", completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["iterations_completed"], 2)
        self.assertEqual(summary["decision_counts"], {"keep": 2})


if __name__ == "__main__":
    unittest.main()
