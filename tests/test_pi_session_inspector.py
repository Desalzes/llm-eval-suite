import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.pi_session_inspector import inspect_pi_session, resolve_latest_pi_session


ROOT = Path(__file__).resolve().parents[1]


class PiSessionInspectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pi-session-inspector-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_jsonl(self, path: Path, rows: list[dict]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        return path

    def _sample_session(self, path: Path) -> Path:
        return self._write_jsonl(
            path,
            [
                {
                    "type": "session",
                    "id": "session-123",
                    "timestamp": "2026-05-26T12:00:00.000Z",
                    "cwd": "C:\\work",
                },
                {
                    "type": "model_change",
                    "provider": "google",
                    "modelId": "gemini-2.5-flash-lite",
                },
                {
                    "type": "thinking_level_change",
                    "thinkingLevel": "medium",
                },
                {
                    "type": "message",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "Summarize AGENTS.md"}],
                    },
                },
                {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "provider": "google",
                        "model": "gemini-2.5-flash-lite",
                        "stopReason": "stop",
                        "usage": {
                            "input": 10,
                            "output": 5,
                            "totalTokens": 15,
                            "cost": {"total": 0.0015},
                        },
                        "content": [
                            {"type": "thinking", "thinking": "Working"},
                            {"type": "text", "text": "Summary complete."},
                        ],
                    },
                },
            ],
        )

    def test_inspect_pi_session_summarizes_core_evidence(self) -> None:
        session_path = self._sample_session(self.temp_dir / "session.jsonl")

        inspected = inspect_pi_session(session_path)

        self.assertEqual(inspected["session_id"], "session-123")
        self.assertEqual(inspected["provider"], "google")
        self.assertEqual(inspected["model"], "gemini-2.5-flash-lite")
        self.assertEqual(inspected["thinking_level"], "medium")
        self.assertEqual(inspected["status"], "passed")
        self.assertEqual(inspected["message_count"], 2)
        self.assertEqual(inspected["user_message_count"], 1)
        self.assertEqual(inspected["assistant_message_count"], 1)
        self.assertEqual(inspected["error_count"], 0)
        self.assertEqual(inspected["total_tokens"], 15)
        self.assertEqual(inspected["total_cost"], 0.0015)
        self.assertEqual(inspected["last_user_text"], "Summarize AGENTS.md")
        self.assertEqual(inspected["last_assistant_text"], "Summary complete.")

    def test_inspect_pi_session_reports_final_error_status(self) -> None:
        session_path = self._write_jsonl(
            self.temp_dir / "failed.jsonl",
            [
                {"type": "session", "id": "failed-session", "timestamp": "2026-05-26T12:00:00.000Z"},
                {"type": "model_change", "provider": "anthropic", "modelId": "claude-opus"},
                {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "provider": "anthropic",
                        "model": "claude-opus",
                        "stopReason": "error",
                        "errorMessage": "No API key for provider: anthropic",
                    },
                },
            ],
        )

        inspected = inspect_pi_session(session_path)

        self.assertEqual(inspected["status"], "failed")
        self.assertEqual(inspected["error_count"], 1)
        self.assertEqual(inspected["last_error"], "No API key for provider: anthropic")

    def test_resolve_latest_pi_session_uses_newest_jsonl(self) -> None:
        older = self._sample_session(self.temp_dir / "older.jsonl")
        newer = self._sample_session(self.temp_dir / "newer.jsonl")
        os.utime(older, (1_000_000, 1_000_000))
        os.utime(newer, (2_000_000, 2_000_000))

        self.assertEqual(resolve_latest_pi_session(self.temp_dir), newer)

    def test_inspect_pi_session_cli_latest_brief(self) -> None:
        session_path = self._sample_session(self.temp_dir / "latest.jsonl")
        os.utime(session_path, (2_000_000, 2_000_000))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-pi-session",
                "--latest",
                "--sessions-dir",
                str(self.temp_dir),
                "--brief",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        inspected = json.loads(completed.stdout)
        self.assertEqual(inspected["session_id"], "session-123")
        self.assertEqual(inspected["status"], "passed")
        self.assertEqual(inspected["total_tokens"], 15)
        self.assertEqual(inspected["last_assistant_text"], "Summary complete.")
