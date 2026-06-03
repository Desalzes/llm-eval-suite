import json
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from suite.cli import main
from suite.supervised_runner import run_supervised_task


ROOT = Path(__file__).resolve().parents[1]


class SupervisedRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="supervised-runner-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_profile(self, profile_id: str, command: list[str]) -> Path:
        profile_path = self.temp_dir / f"{profile_id}.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": profile_id,
                    "name": profile_id,
                    "description": f"{profile_id} test profile.",
                    "command": command,
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def test_supervised_task_runs_child_session_and_scores_passed(self) -> None:
        profile_path = self._write_profile(
            "supervised-fixer",
            [
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
        )

        result = run_supervised_task(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=profile_path,
            run_id="unit-supervised-pass",
            runs_dir=self.temp_dir / "supervised-runs",
            timeout_seconds=15,
            idle_timeout_seconds=15,
            max_output_bytes=4096,
            force=True,
        )

        run_dir = Path(result["run_dir"])
        prompt = (run_dir / "prompt.md").read_text(encoding="utf-8")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["child_status"], "passed")
        self.assertEqual(result["test_exit_code"], 0)
        self.assertEqual(result["changed_files"], ["calculator.py"])
        self.assertEqual(result["forbidden_changed_files"], [])
        self.assertEqual(len(result["prompt_sha256"]), 64)
        self.assertEqual(len(result["profile_command_sha256"]), 64)
        self.assertIn("## Supervision Protocol", prompt)
        self.assertIn("Use relevant local skills", prompt)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["prompt_sha256"], result["prompt_sha256"])
        self.assertEqual(manifest["profile_command_sha256"], result["profile_command_sha256"])
        self.assertTrue((run_dir / "child" / "transcript.txt").exists())
        self.assertTrue((run_dir / "test-output.txt").exists())
        self.assertTrue((run_dir / "diff.patch").exists())
        self.assertTrue((run_dir / "result.json").exists())

    def test_supervised_task_marks_forbidden_child_edits_unsafe(self) -> None:
        profile_path = self._write_profile(
            "supervised-unsafe",
            [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('notes.txt').write_text('unsafe', encoding='utf-8')",
            ],
        )

        result = run_supervised_task(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=profile_path,
            run_id="unit-supervised-unsafe",
            runs_dir=self.temp_dir / "supervised-runs",
            timeout_seconds=15,
            idle_timeout_seconds=15,
            max_output_bytes=4096,
            force=True,
        )

        self.assertEqual(result["status"], "unsafe")
        self.assertEqual(result["child_status"], "unsafe")
        self.assertIn("notes.txt", result["changed_files"])
        self.assertIn("notes.txt", result["forbidden_changed_files"])

    def test_supervise_task_cli_runs_bounded_task(self) -> None:
        profile_path = self._write_profile(
            "supervised-cli-fixer",
            [
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
        )
        runs_dir = self.temp_dir / "supervised-runs"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "supervise-task",
                "--task",
                str(ROOT / "tasks/examples/python-cli-bugfix/task.json"),
                "--profile",
                str(profile_path),
                "--run-id",
                "cli-supervised-pass",
                "--runs-dir",
                str(runs_dir),
                "--timeout-seconds",
                "15",
                "--idle-timeout-seconds",
                "15",
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
        self.assertIn("[supervise-task] starting cli-supervised-pass", completed.stderr)
        self.assertIn("[supervise-task] cli-supervised-pass -> passed", completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "passed")
        self.assertTrue((runs_dir / "cli-supervised-pass" / "child" / "result.json").exists())

    def test_supervise_task_cli_fails_fast_when_codex_auth_is_missing(self) -> None:
        profile_path = self._write_profile("codex-like", ["codex.cmd", "exec", "-"])

        argv = [
            "suite.cli",
            "supervise-task",
            "--task",
            str(ROOT / "tasks/examples/python-cli-bugfix/task.json"),
            "--profile",
            str(profile_path),
            "--run-id",
            "missing-auth",
        ]

        with (
            patch.object(sys, "argv", argv),
            patch("sys.stderr", io.StringIO()),
            patch("suite.cli._has_codex_auth", return_value=False),
            patch("suite.cli.run_supervised_task") as run_task,
        ):
            with self.assertRaises(SystemExit) as raised:
                main()

        self.assertEqual(raised.exception.code, 2)
        run_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
