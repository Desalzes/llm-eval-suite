import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.codex_session_inspector import inspect_codex_session, resolve_latest_codex_session


ROOT = Path(__file__).resolve().parents[1]


class CodexSessionInspectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="codex-session-inspector-test-"))

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
                    "timestamp": "2026-05-27T17:59:25.645Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "019e6a97-3608-7633-81fd-f41a316d29ca",
                        "timestamp": "2026-05-27T17:59:20.218Z",
                        "cwd": "C:\\work",
                        "originator": "codex_cli_rs",
                        "cli_version": "0.133.0",
                        "source": "cli",
                        "model_provider": "openai",
                    },
                },
                {
                    "timestamp": "2026-05-27T17:59:34.615Z",
                    "type": "turn_context",
                    "payload": {
                        "turn_id": "turn-1",
                        "cwd": "C:\\work",
                        "model": "gpt-5.5",
                        "approval_policy": "never",
                        "sandbox_policy": {"type": "workspace-write"},
                    },
                },
                {
                    "timestamp": "2026-05-27T17:59:35.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "Summarize AGENTS.md"}],
                    },
                },
                {
                    "timestamp": "2026-05-27T17:59:40.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "shell",
                        "arguments": "{\"command\":[\"git\",\"status\"]}",
                    },
                },
                {
                    "timestamp": "2026-05-27T17:59:42.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {
                                "input_tokens": 1200,
                                "cached_input_tokens": 100,
                                "output_tokens": 400,
                                "reasoning_output_tokens": 150,
                                "total_tokens": 1600,
                            }
                        },
                    },
                },
                {
                    "timestamp": "2026-05-27T17:59:45.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "Summary complete."}],
                    },
                },
                {
                    "timestamp": "2026-05-27T17:59:46.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": "turn-1",
                        "last_agent_message": "Summary complete.",
                    },
                },
            ],
        )

    def test_inspect_codex_session_summarizes_core_evidence(self) -> None:
        session_path = self._sample_session(self.temp_dir / "session.jsonl")

        inspected = inspect_codex_session(session_path)

        self.assertEqual(inspected["session_id"], "019e6a97-3608-7633-81fd-f41a316d29ca")
        self.assertEqual(inspected["provider"], "openai")
        self.assertEqual(inspected["model"], "gpt-5.5")
        self.assertEqual(inspected["cli_version"], "0.133.0")
        self.assertEqual(inspected["originator"], "codex_cli_rs")
        self.assertEqual(inspected["source"], "cli")
        self.assertEqual(inspected["status"], "passed")
        self.assertEqual(inspected["message_count"], 2)
        self.assertEqual(inspected["user_message_count"], 1)
        self.assertEqual(inspected["assistant_message_count"], 1)
        self.assertEqual(inspected["tool_call_count"], 1)
        self.assertEqual(inspected["task_complete_count"], 1)
        self.assertEqual(inspected["error_count"], 0)
        self.assertEqual(inspected["total_tokens"], 1600)
        self.assertEqual(inspected["total_input_tokens"], 1200)
        self.assertEqual(inspected["total_output_tokens"], 400)
        self.assertEqual(inspected["total_reasoning_output_tokens"], 150)
        self.assertEqual(inspected["cached_input_tokens"], 100)
        self.assertEqual(inspected["last_user_text"], "Summarize AGENTS.md")
        self.assertEqual(inspected["last_assistant_text"], "Summary complete.")

    def test_inspect_codex_session_reports_failure_when_error_event_present(self) -> None:
        session_path = self._write_jsonl(
            self.temp_dir / "failed.jsonl",
            [
                {
                    "timestamp": "2026-05-27T17:59:25.645Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "failed-session",
                        "timestamp": "2026-05-27T17:59:20.218Z",
                        "model_provider": "openai",
                    },
                },
                {
                    "timestamp": "2026-05-27T17:59:30.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "error",
                        "message": "Codex sandbox blocked the requested write.",
                    },
                },
            ],
        )

        inspected = inspect_codex_session(session_path)

        self.assertEqual(inspected["status"], "failed")
        self.assertEqual(inspected["error_count"], 1)
        self.assertEqual(inspected["last_error"], "Codex sandbox blocked the requested write.")

    def test_inspect_codex_session_passes_when_assistant_replies_without_task_complete(self) -> None:
        session_path = self._write_jsonl(
            self.temp_dir / "subagent.jsonl",
            [
                {
                    "timestamp": "2026-05-27T17:59:25.645Z",
                    "type": "session_meta",
                    "payload": {"id": "subagent-session", "model_provider": "openai"},
                },
                {
                    "timestamp": "2026-05-27T17:59:35.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "Subagent response."}],
                    },
                },
            ],
        )

        inspected = inspect_codex_session(session_path)

        self.assertEqual(inspected["status"], "passed")
        self.assertEqual(inspected["task_complete_count"], 0)
        self.assertEqual(inspected["last_assistant_text"], "Subagent response.")

    def test_resolve_latest_codex_session_walks_nested_date_dirs(self) -> None:
        older = self._sample_session(self.temp_dir / "2026" / "05" / "26" / "rollout-older.jsonl")
        newer = self._sample_session(self.temp_dir / "2026" / "05" / "27" / "rollout-newer.jsonl")
        os.utime(older, (1_000_000, 1_000_000))
        os.utime(newer, (2_000_000, 2_000_000))

        self.assertEqual(resolve_latest_codex_session(self.temp_dir), newer)

    def test_inspect_codex_session_cli_latest_brief(self) -> None:
        session_dir = self.temp_dir / "2026" / "05" / "27"
        session_path = self._sample_session(session_dir / "rollout.jsonl")
        os.utime(session_path, (2_000_000, 2_000_000))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "inspect-codex-session",
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
        self.assertEqual(inspected["session_id"], "019e6a97-3608-7633-81fd-f41a316d29ca")
        self.assertEqual(inspected["status"], "passed")
        self.assertEqual(inspected["total_tokens"], 1600)
        self.assertEqual(inspected["last_assistant_text"], "Summary complete.")
