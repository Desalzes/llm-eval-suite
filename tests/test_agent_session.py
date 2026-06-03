import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.agent_session import run_agent_session


ROOT = Path(__file__).resolve().parents[1]


class AgentSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="agent-session-test-"))

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

    def _write_prompt(self, text: str = "Run native agent.\n") -> Path:
        prompt_file = self.temp_dir / "prompt.md"
        prompt_file.write_text(text, encoding="utf-8")
        return prompt_file

    def _make_workspace(self) -> Path:
        workspace = self.temp_dir / "workspace"
        workspace.mkdir(exist_ok=True)
        return workspace

    def _write_pi_jsonl_script(
        self,
        sessions_dir: Path,
        payload: list[dict],
        name: str = "write_pi_session.py",
        target_names: list[str] | None = None,
    ) -> Path:
        targets = target_names or ["pi-session-123.jsonl"]
        script_path = self.temp_dir / name
        script_path.write_text(
            "\n".join(
                [
                    "import json",
                    "from pathlib import Path",
                    f"sessions_dir = Path({str(sessions_dir)!r})",
                    f"rows = json.loads({json.dumps(payload)!r})",
                    f"target_names = {json.dumps(targets)}",
                    "sessions_dir.mkdir(parents=True, exist_ok=True)",
                    "for target_name in target_names:",
                    "    target = sessions_dir / target_name",
                    "    target.write_text(''.join(json.dumps(row) + '\\n' for row in rows), encoding='utf-8')",
                    "print('PI SESSION WRITTEN', flush=True)",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return script_path

    def _write_sample_pi_jsonl_script(self, sessions_dir: Path, cwd: Path | None = None) -> Path:
        payload = [
            {
                "type": "session",
                "id": "pi-session-123",
                "timestamp": "2026-05-26T12:00:00.000Z",
                "cwd": str(cwd) if cwd is not None else "C:\\work",
            },
            {"type": "model_change", "provider": "google", "modelId": "gemini-2.5-flash-lite"},
            {"type": "thinking_level_change", "thinkingLevel": "medium"},
            {
                "type": "message",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Run native agent."}],
                },
            },
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "provider": "google",
                    "model": "gemini-2.5-flash-lite",
                    "stopReason": "stop",
                    "usage": {"totalTokens": 21, "cost": {"total": 0.0021}},
                    "content": [{"type": "text", "text": "Pi run complete."}],
                },
            },
        ]
        return self._write_pi_jsonl_script(sessions_dir, payload)

    def _write_ambiguous_pi_jsonl_script(self, sessions_dir: Path, cwd: Path) -> Path:
        payload = [
            {
                "type": "session",
                "id": "pi-session-ambiguous",
                "timestamp": "2026-05-26T12:00:00.000Z",
                "cwd": str(cwd),
            },
            {"type": "model_change", "provider": "google", "modelId": "gemini-2.5-flash-lite"},
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "provider": "google",
                    "model": "gemini-2.5-flash-lite",
                    "stopReason": "stop",
                    "content": [{"type": "text", "text": "Ambiguous Pi run."}],
                },
            },
        ]
        return self._write_pi_jsonl_script(
            sessions_dir,
            payload,
            name="write_ambiguous_pi_sessions.py",
            target_names=["pi-session-123.jsonl", "pi-session-456.jsonl"],
        )

    def _write_failed_pi_jsonl_script(self, sessions_dir: Path) -> Path:
        payload = [
            {"type": "session", "id": "pi-session-123", "timestamp": "2026-05-26T12:00:00.000Z"},
            {"type": "model_change", "provider": "google", "modelId": "gemini-2.5-flash-lite"},
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "provider": "google",
                    "model": "gemini-2.5-flash-lite",
                    "stopReason": "error",
                    "errorMessage": "No API key for provider: google",
                },
            },
        ]
        return self._write_pi_jsonl_script(sessions_dir, payload, name="write_failed_pi_session.py")

    def test_run_agent_session_command_backend_writes_native_contract(self) -> None:
        workspace = self._make_workspace()
        profile_path = self._write_profile(
            "native-echo",
            [
                sys.executable,
                "-c",
                "import sys; print('NATIVE READY', flush=True); print(sys.stdin.read(), end='', flush=True)",
            ],
        )
        prompt_file = self._write_prompt()

        result = run_agent_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="native-command",
            agent_sessions_dir=self.temp_dir / "agent-runs",
            workspace=workspace,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        session_dir = Path(result["session_dir"])
        manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))
        transcript = (session_dir / "transcript.txt").read_text(encoding="utf-8")

        self.assertEqual(result["session_type"], "suite-agent-session")
        self.assertEqual(result["contract_version"], 1)
        self.assertEqual(result["run_id"], "native-command")
        self.assertEqual(result["backend"], "command")
        self.assertEqual(result["status"], "passed")
        self.assertIsNone(result["pi_session"])
        self.assertEqual(manifest["session_type"], "suite-agent-session")
        self.assertEqual(manifest["contract_version"], 1)
        self.assertEqual(manifest["backend"], "command")
        self.assertIn("NATIVE READY", transcript)
        self.assertTrue((session_dir / "events.jsonl").exists())
        self.assertTrue((session_dir / "changes.json").exists())
        self.assertTrue((session_dir / "trace-summary.json").exists())

    def test_agent_run_cli_command_backend_writes_artifacts(self) -> None:
        workspace = self._make_workspace()
        profile_path = self._write_profile(
            "native-cli-echo",
            [
                sys.executable,
                "-c",
                "import sys; print('CLI NATIVE READY', flush=True); print(sys.stdin.read(), end='', flush=True)",
            ],
        )
        prompt_file = self._write_prompt("Run native CLI.\n")
        sessions_dir = self.temp_dir / "agent-runs"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "agent",
                "run",
                "--profile",
                str(profile_path),
                "--prompt-file",
                str(prompt_file),
                "--agent-runs-dir",
                str(sessions_dir),
                "--workspace",
                str(workspace),
                "--session-id",
                "native-cli",
                "--backend",
                "command",
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
        self.assertIn("[agent-session] starting native-cli", completed.stderr)
        summary = json.loads(completed.stdout)
        transcript = (sessions_dir / "native-cli" / "transcript.txt").read_text(encoding="utf-8")
        self.assertEqual(summary["session_type"], "suite-agent-session")
        self.assertEqual(summary["backend"], "command")
        self.assertEqual(summary["status"], "passed")
        self.assertIn("CLI NATIVE READY", transcript)
        self.assertIn("Run native CLI.", transcript)

    def test_agent_run_pi_backend_attaches_latest_pi_inspection(self) -> None:
        workspace = self._make_workspace()
        pi_sessions_dir = self.temp_dir / "pi-sessions"
        script_path = self._write_sample_pi_jsonl_script(pi_sessions_dir, cwd=workspace)
        profile_path = self._write_profile(
            "fake-pi",
            [sys.executable, str(script_path)],
        )
        prompt_file = self._write_prompt()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "agent",
                "run",
                "--profile",
                str(profile_path),
                "--prompt-file",
                str(prompt_file),
                "--agent-runs-dir",
                str(self.temp_dir / "agent-runs"),
                "--workspace",
                str(workspace),
                "--pi-sessions-dir",
                str(pi_sessions_dir),
                "--session-id",
                "native-pi",
                "--backend",
                "pi",
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
        summary = json.loads(completed.stdout)
        manifest = json.loads(
            (
                self.temp_dir
                / "agent-runs"
                / "native-pi"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(summary["backend"], "pi")
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["pi_session_candidate_count"], 1)
        self.assertEqual(manifest["pi_session_candidate_count"], 1)
        self.assertEqual(summary["pi_session"]["session_id"], "pi-session-123")
        self.assertEqual(summary["pi_session"]["provider"], "google")
        self.assertEqual(summary["pi_session"]["model"], "gemini-2.5-flash-lite")
        self.assertEqual(summary["pi_session"]["total_tokens"], 21)
        self.assertEqual(summary["pi_session"]["last_assistant_text"], "Pi run complete.")
        self.assertEqual(Path(summary["pi_session"]["cwd"]), workspace)
        self.assertEqual(summary["final_response"], "Pi run complete.")

    def test_agent_run_pi_backend_fails_on_multiple_changed_transcripts(self) -> None:
        workspace = self._make_workspace()
        pi_sessions_dir = self.temp_dir / "pi-sessions"
        script_path = self._write_ambiguous_pi_jsonl_script(pi_sessions_dir, workspace)
        profile_path = self._write_profile("fake-pi-ambiguous", [sys.executable, str(script_path)])
        prompt_file = self._write_prompt()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "agent",
                "run",
                "--profile",
                str(profile_path),
                "--prompt-file",
                str(prompt_file),
                "--agent-runs-dir",
                str(self.temp_dir / "agent-runs"),
                "--workspace",
                str(workspace),
                "--pi-sessions-dir",
                str(pi_sessions_dir),
                "--session-id",
                "native-pi-ambiguous",
                "--backend",
                "pi",
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

        self.assertEqual(completed.returncode, 1, completed.stderr + completed.stdout)
        summary = json.loads(completed.stdout)
        manifest = json.loads(
            (
                self.temp_dir
                / "agent-runs"
                / "native-pi-ambiguous"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(summary["terminal_status"], "passed")
        self.assertEqual(summary["status"], "failed")
        self.assertIsNone(summary["pi_session"])
        self.assertEqual(summary["pi_session_status"], "ambiguous")
        self.assertEqual(summary["pi_attach_error"], "ambiguous_pi_session_candidates")
        self.assertEqual(len(summary["pi_session_candidates"]), 2)
        self.assertEqual(manifest["pi_attach_error"], "ambiguous_pi_session_candidates")
        self.assertEqual(manifest["pi_session_candidate_count"], 2)

    def test_agent_run_pi_backend_fails_when_pi_transcript_failed(self) -> None:
        workspace = self._make_workspace()
        pi_sessions_dir = self.temp_dir / "pi-sessions"
        script_path = self._write_failed_pi_jsonl_script(pi_sessions_dir)
        profile_path = self._write_profile("fake-pi-fail", [sys.executable, str(script_path)])
        prompt_file = self._write_prompt()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "agent",
                "run",
                "--profile",
                str(profile_path),
                "--prompt-file",
                str(prompt_file),
                "--agent-runs-dir",
                str(self.temp_dir / "agent-runs"),
                "--workspace",
                str(workspace),
                "--pi-sessions-dir",
                str(pi_sessions_dir),
                "--session-id",
                "native-pi-fail",
                "--backend",
                "pi",
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

        self.assertEqual(completed.returncode, 1, completed.stderr + completed.stdout)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["terminal_status"], "passed")
        self.assertEqual(summary["pi_session"]["status"], "failed")
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["last_error"], "No API key for provider: google")

    def test_inspect_agent_session_cli_latest_brief(self) -> None:
        workspace = self._make_workspace()
        profile_path = self._write_profile(
            "native-inspect",
            [sys.executable, "-c", "print('INSPECT READY', flush=True)"],
        )
        prompt_file = self._write_prompt()
        sessions_dir = self.temp_dir / "agent-runs"
        run_agent_session(
            suite_root=ROOT,
            profile_path=profile_path,
            prompt_file=prompt_file,
            session_id="native-inspect",
            agent_sessions_dir=sessions_dir,
            workspace=workspace,
            backend="command",
            timeout_seconds=5,
            idle_timeout_seconds=5,
            max_output_bytes=4096,
            force=True,
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-agent-session",
                "--latest",
                "--agent-runs-dir",
                str(sessions_dir),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        inspected = json.loads(completed.stdout)
        self.assertEqual(inspected["session_id"], "native-inspect")
        self.assertEqual(inspected["session_type"], "suite-agent-session")
        self.assertEqual(inspected["backend"], "command")
        self.assertEqual(inspected["status"], "passed")
        self.assertEqual(inspected["profile_id"], "native-inspect")


if __name__ == "__main__":
    unittest.main()
