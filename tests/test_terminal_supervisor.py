import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import queue
from pathlib import Path

from suite.terminal_supervisor import _read_output, run_terminal_session


ROOT = Path(__file__).resolve().parents[1]


class TerminalSupervisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="terminal-supervisor-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_profile(self, name: str, command: list[str]) -> Path:
        profile_path = self.temp_dir / f"{name}.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": name,
                    "name": name,
                    "description": f"{name} test profile.",
                    "command": command,
                }
            ),
            encoding="utf-8",
        )
        return profile_path

    def test_output_reader_treats_closed_stream_as_end_of_stream(self) -> None:
        class ClosedStream:
            def read(self, _size: int) -> bytes:
                raise ValueError("I/O operation on closed file")

        output_queue: queue.Queue[bytes] = queue.Queue()

        _read_output(ClosedStream(), output_queue)

        self.assertEqual(output_queue.get_nowait(), b"")

    def test_supervisor_sends_prompt_and_captures_transcript(self) -> None:
        profile_path = self._write_profile(
            "echo-child",
            [
                sys.executable,
                "-c",
                "import sys; print('READY', flush=True); print(sys.stdin.read(), end='', flush=True)",
            ],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Build the fixture.\n", encoding="utf-8")

        result = run_terminal_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="unit-echo",
            sessions_dir=self.temp_dir / "terminal-runs",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        session_dir = Path(result["session_dir"])
        transcript = (session_dir / "transcript.txt").read_text(encoding="utf-8")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(len(result["prompt_sha256"]), 64)
        self.assertIn("READY", transcript)
        self.assertIn("Build the fixture.", transcript)
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["prompt_sha256"], result["prompt_sha256"])
        self.assertTrue((session_dir / "events.jsonl").exists())
        self.assertTrue((session_dir / "result.json").exists())
        self.assertTrue((session_dir / "trace-summary.json").exists())

    def test_supervisor_stops_when_output_cap_is_exceeded(self) -> None:
        profile_path = self._write_profile(
            "spam-child",
            [sys.executable, "-c", "print('x' * 20000, flush=True)"],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Start.\n", encoding="utf-8")

        result = run_terminal_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="unit-output-cap",
            sessions_dir=self.temp_dir / "terminal-runs",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=1024,
            force=True,
        )

        self.assertEqual(result["status"], "capped")
        self.assertEqual(result["cap_reason"], "max_output_bytes")
        self.assertGreaterEqual(result["output_bytes"], 1024)

    def test_supervisor_stops_when_timeout_is_exceeded(self) -> None:
        profile_path = self._write_profile(
            "slow-child",
            [sys.executable, "-c", "import time; print('START', flush=True); time.sleep(5)"],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Start.\n", encoding="utf-8")

        result = run_terminal_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="unit-timeout",
            sessions_dir=self.temp_dir / "terminal-runs",
            timeout_seconds=0.2,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["cap_reason"], "timeout_seconds")

    def test_supervisor_records_allowed_workspace_changes(self) -> None:
        workspace = self.temp_dir / "workspace"
        workspace.mkdir()
        profile_path = self._write_profile(
            "allowed-writer",
            [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('allowed.txt').write_text('ok', encoding='utf-8')",
            ],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Write allowed file.\n", encoding="utf-8")

        result = run_terminal_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="unit-allowed-change",
            sessions_dir=self.temp_dir / "terminal-runs",
            workspace=workspace,
            allowed_paths=["allowed.txt"],
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        session_dir = Path(result["session_dir"])
        changes = json.loads((session_dir / "changes.json").read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["changed_files"], ["allowed.txt"])
        self.assertEqual(result["forbidden_changed_files"], [])
        self.assertEqual(changes["changed_files"], ["allowed.txt"])

    def test_supervisor_ignores_pytest_temp_workspace_changes(self) -> None:
        workspace = self.temp_dir / "workspace"
        workspace.mkdir()
        profile_path = self._write_profile(
            "pytest-temp-writer",
            [
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    "path = Path('.pytest-tmp/pytest-of-user/test_example0/output.txt'); "
                    "path.parent.mkdir(parents=True); "
                    "path.write_text('runtime only', encoding='utf-8')"
                ),
            ],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Run pytest-like temp work.\n", encoding="utf-8")

        result = run_terminal_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="unit-pytest-temp",
            sessions_dir=self.temp_dir / "terminal-runs",
            workspace=workspace,
            allowed_paths=[],
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["changed_files"], [])
        self.assertEqual(result["forbidden_changed_files"], [])

    def test_supervisor_marks_forbidden_workspace_changes_unsafe(self) -> None:
        workspace = self.temp_dir / "workspace"
        workspace.mkdir()
        profile_path = self._write_profile(
            "unsafe-writer",
            [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('blocked.txt').write_text('unsafe', encoding='utf-8')",
            ],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Write blocked file.\n", encoding="utf-8")

        result = run_terminal_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="unit-forbidden-change",
            sessions_dir=self.temp_dir / "terminal-runs",
            workspace=workspace,
            allowed_paths=["allowed.txt"],
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        self.assertEqual(result["status"], "unsafe")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["changed_files"], ["blocked.txt"])
        self.assertEqual(result["forbidden_changed_files"], ["blocked.txt"])

    def test_supervisor_defaults_to_no_workspace_changes_allowed(self) -> None:
        workspace = self.temp_dir / "workspace"
        workspace.mkdir()
        profile_path = self._write_profile(
            "default-unsafe-writer",
            [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('unexpected.txt').write_text('unsafe', encoding='utf-8')",
            ],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Do not write files.\n", encoding="utf-8")

        result = run_terminal_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="unit-default-no-edits",
            sessions_dir=self.temp_dir / "terminal-runs",
            workspace=workspace,
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        self.assertEqual(result["status"], "unsafe")
        self.assertEqual(result["changed_files"], ["unexpected.txt"])
        self.assertEqual(result["forbidden_changed_files"], ["unexpected.txt"])

    def test_supervise_terminal_cli_writes_artifacts(self) -> None:
        profile_path = self._write_profile(
            "cli-echo-child",
            [
                sys.executable,
                "-c",
                "import sys; print('CLI READY', flush=True); print(sys.stdin.read(), end='', flush=True)",
            ],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Run from CLI.\n", encoding="utf-8")
        sessions_dir = self.temp_dir / "terminal-runs"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "supervise-terminal",
                "--profile",
                str(profile_path),
                "--prompt-file",
                str(prompt_file),
                "--terminal-runs-dir",
                str(sessions_dir),
                "--session-id",
                "cli-session",
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
        self.assertIn("[terminal-supervisor] starting cli-session", completed.stderr)
        self.assertIn("[terminal-supervisor] cli-session -> passed", completed.stderr)
        summary = json.loads(completed.stdout)
        transcript = (sessions_dir / "cli-session" / "transcript.txt").read_text(encoding="utf-8")
        self.assertEqual(summary["status"], "passed")
        self.assertIn("CLI READY", transcript)
        self.assertIn("Run from CLI.", transcript)

    def test_supervise_terminal_cli_reports_missing_prompt_file(self) -> None:
        profile_path = self._write_profile(
            "cli-missing-prompt-child",
            [sys.executable, "-c", "print('should not run')"],
        )
        missing_prompt = self.temp_dir / "missing.md"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "supervise-terminal",
                "--profile",
                str(profile_path),
                "--prompt-file",
                str(missing_prompt),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("prompt file does not exist", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_supervise_terminal_cli_accepts_allowed_paths(self) -> None:
        workspace = self.temp_dir / "workspace"
        workspace.mkdir()
        profile_path = self._write_profile(
            "cli-allowed-writer",
            [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('allowed.txt').write_text('ok', encoding='utf-8')",
            ],
        )
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text("Write from CLI.\n", encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "supervise-terminal",
                "--profile",
                str(profile_path),
                "--prompt-file",
                str(prompt_file),
                "--workspace",
                str(workspace),
                "--terminal-runs-dir",
                str(self.temp_dir / "terminal-runs"),
                "--session-id",
                "cli-allowed-session",
                "--allowed-path",
                "allowed.txt",
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
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["changed_files"], ["allowed.txt"])


if __name__ == "__main__":
    unittest.main()
