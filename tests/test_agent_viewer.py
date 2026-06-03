import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from suite.agent_viewer import (
    LIVE_STALE_AFTER_SECONDS,
    list_agent_sessions,
    read_agent_session,
    read_agent_session_live,
    summarize_live_sessions,
)


class AgentViewerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="agent-viewer-test-"))
        self.runs_dir = self.temp_dir / "agent-runs"
        self.runs_dir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_session(self, session_id: str, *, backend: str = "command", include_pi: bool = False) -> Path:
        session_dir = self.runs_dir / session_id
        session_dir.mkdir()
        pi_session = None
        if include_pi:
            pi_session = {
                "session_id": "pi-123",
                "status": "passed",
                "provider": "google",
                "model": "gemini-2.5-flash-lite",
                "total_tokens": 42,
                "total_cost": 0.0042,
                "last_assistant_text": "Pi final response.",
            }
        top_level_provider = "ignored-top-level-provider" if pi_session else None
        top_level_model = "ignored-top-level-model" if pi_session else None
        top_level_total_tokens = 999 if pi_session else None
        top_level_total_cost = 9.99 if pi_session else None
        top_level_final_response = "Ignored top-level response." if pi_session else None
        self._write_json(
            session_dir / "result.json",
            {
                "session_id": session_id,
                "session_type": "suite-agent-session",
                "contract_version": 1,
                "backend": backend,
                "status": "passed",
                "terminal_status": "passed",
                "pi_session_status": pi_session["status"] if pi_session else None,
                "profile_id": "unit-profile",
                "provider": top_level_provider,
                "model": top_level_model,
                "duration_seconds": 1.25,
                "total_tokens": top_level_total_tokens,
                "total_cost": top_level_total_cost,
                "final_response": top_level_final_response,
                "changed_files": ["allowed.txt"],
                "forbidden_changed_files": [],
                "pi_session": pi_session,
            },
        )
        self._write_json(
            session_dir / "manifest.json",
            {"session_id": session_id, "profile_id": "unit-profile", "backend": backend},
        )
        self._write_json(session_dir / "changes.json", {"changed_files": ["allowed.txt"], "forbidden_changed_files": []})
        self._write_json(session_dir / "trace-summary.json", {"tool_call_count": 2})
        (session_dir / "events.jsonl").write_text(
            json.dumps({"type": "start", "session_id": session_id}) + "\n"
            + json.dumps({"type": "finish", "status": "passed"}) + "\n",
            encoding="utf-8",
        )
        (session_dir / "transcript.txt").write_text("=== child output ===\nHello from child.\n", encoding="utf-8")
        return session_dir

    def _write_running_session(
        self,
        session_id: str,
        *,
        start_time: datetime,
        last_event_time: datetime | None = None,
        transcript_text: str = "=== child output ===\nfirst line\nlatest child output\n",
    ) -> Path:
        session_dir = self.runs_dir / session_id
        session_dir.mkdir()
        manifest_path = session_dir / "manifest.json"
        events_path = session_dir / "events.jsonl"
        transcript_path = session_dir / "transcript.txt"
        self._write_json(
            manifest_path,
            {
                "session_id": session_id,
                "profile_id": "unit-profile",
                "backend": "command",
                "command": ["python", "-c", "print('running')"],
            },
        )
        events = [
            {"time": start_time.isoformat(timespec="seconds"), "event": "start", "session_id": session_id},
        ]
        if last_event_time is not None:
            events.append(
                {
                    "time": last_event_time.isoformat(timespec="seconds"),
                    "event": "output",
                    "bytes": 19,
                    "total_output_bytes": 29,
                    "preview": "latest child output",
                }
            )
        events_path.write_text(
            "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
            encoding="utf-8",
        )
        transcript_path.write_text(transcript_text, encoding="utf-8")
        import os

        artifact_time = (last_event_time or start_time).timestamp()
        for artifact_path in [manifest_path, events_path, transcript_path]:
            os.utime(artifact_path, (artifact_time, artifact_time))
        return session_dir

    def test_list_agent_sessions_orders_newest_first(self) -> None:
        newer = self._write_session("newer", backend="pi", include_pi=True)
        older = self._write_session("older")
        older_time = 1_000_000
        newer_time = 2_000_000
        import os
        os.utime(older / "result.json", (older_time, older_time))
        os.utime(newer / "result.json", (newer_time, newer_time))
        os.utime(older, (newer_time, newer_time))
        os.utime(newer, (older_time, older_time))

        sessions = list_agent_sessions(self.runs_dir)

        self.assertEqual([item["session_id"] for item in sessions], ["newer", "older"])
        self.assertEqual(sessions[0]["backend"], "pi")
        self.assertEqual(sessions[0]["status"], "passed")

    def test_read_agent_session_normalizes_pi_session(self) -> None:
        session_dir = self._write_session("native-pi", backend="pi", include_pi=True)
        result = json.loads((session_dir / "result.json").read_text(encoding="utf-8"))

        detail = read_agent_session(session_dir)

        self.assertTrue(detail["readable"])
        self.assertEqual(detail["session_id"], "native-pi")
        self.assertEqual(detail["backend"], "pi")
        self.assertNotEqual(result["provider"], "google")
        self.assertNotEqual(result["model"], "gemini-2.5-flash-lite")
        self.assertNotEqual(result["total_tokens"], 42)
        self.assertNotEqual(result["total_cost"], 0.0042)
        self.assertNotEqual(result["final_response"], "Pi final response.")
        self.assertEqual(detail["provider"], "google")
        self.assertEqual(detail["model"], "gemini-2.5-flash-lite")
        self.assertEqual(detail["total_tokens"], 42)
        self.assertEqual(detail["total_cost"], 0.0042)
        self.assertEqual(detail["final_response"], "Pi final response.")
        self.assertEqual(detail["safety"]["forbidden_count"], 0)
        self.assertEqual(detail["availability"]["pi_session"], "available")
        self.assertEqual(detail["timeline"]["events"][0]["type"], "start")
        self.assertIn("Hello from child.", detail["artifacts"]["transcript"])

    def test_read_agent_session_handles_missing_optional_artifacts(self) -> None:
        session_dir = self.runs_dir / "minimal"
        session_dir.mkdir()
        self._write_json(
            session_dir / "result.json",
            {
                "session_id": "minimal",
                "session_type": "suite-agent-session",
                "contract_version": 1,
                "backend": "command",
                "status": "passed",
            },
        )

        detail = read_agent_session(session_dir)

        self.assertTrue(detail["readable"])
        self.assertEqual(detail["availability"]["manifest"], "unavailable")
        self.assertEqual(detail["availability"]["events"], "unavailable")
        self.assertEqual(detail["availability"]["transcript"], "unavailable")
        self.assertEqual(detail["timeline"]["events"], [])

    def test_read_agent_session_reports_malformed_events(self) -> None:
        session_dir = self._write_session("bad-events")
        (session_dir / "events.jsonl").write_text("{bad json\n", encoding="utf-8")

        detail = read_agent_session(session_dir)

        self.assertEqual(detail["availability"]["events"], "malformed")
        self.assertEqual(detail["timeline"]["events"], [])
        self.assertIn("line 1", detail["timeline"]["parse_error"])

    def test_read_agent_session_without_result_is_unreadable(self) -> None:
        session_dir = self.runs_dir / "broken"
        session_dir.mkdir()

        detail = read_agent_session(session_dir)

        self.assertFalse(detail["readable"])
        self.assertEqual(detail["session_id"], "broken")
        self.assertEqual(detail["availability"]["result"], "unavailable")

    def test_read_agent_session_without_result_uses_changes_safety(self) -> None:
        session_dir = self.runs_dir / "broken-with-changes"
        session_dir.mkdir()
        self._write_json(
            session_dir / "changes.json",
            {
                "changed_files": ["allowed.txt", "forbidden.txt"],
                "forbidden_changed_files": ["forbidden.txt"],
            },
        )

        detail = read_agent_session(session_dir)

        self.assertFalse(detail["readable"])
        self.assertEqual(detail["availability"]["result"], "unavailable")
        self.assertEqual(detail["availability"]["changes"], "available")
        self.assertEqual(detail["safety"]["changed_files"], ["allowed.txt", "forbidden.txt"])
        self.assertEqual(detail["safety"]["forbidden_changed_files"], ["forbidden.txt"])
        self.assertEqual(detail["safety"]["forbidden_count"], 1)

    def test_read_agent_session_with_malformed_result_uses_changes_safety(self) -> None:
        session_dir = self.runs_dir / "malformed-with-changes"
        session_dir.mkdir()
        (session_dir / "result.json").write_text("{bad json\n", encoding="utf-8")
        self._write_json(
            session_dir / "changes.json",
            {
                "changed_files": ["allowed.txt", "forbidden.txt"],
                "forbidden_changed_files": ["forbidden.txt"],
            },
        )

        detail = read_agent_session(session_dir)

        self.assertFalse(detail["readable"])
        self.assertEqual(detail["availability"]["result"], "malformed")
        self.assertEqual(detail["availability"]["changes"], "available")
        self.assertEqual(detail["safety"]["changed_files"], ["allowed.txt", "forbidden.txt"])
        self.assertEqual(detail["safety"]["forbidden_changed_files"], ["forbidden.txt"])
        self.assertEqual(detail["safety"]["forbidden_count"], 1)

    def test_read_agent_session_marks_existing_unreadable_json_artifacts_malformed(self) -> None:
        session_dir = self._write_session("unreadable-json")
        (session_dir / "manifest.json").write_bytes(b'{"profile_id": "\xff"}')
        (session_dir / "changes.json").unlink()
        (session_dir / "changes.json").mkdir()

        detail = read_agent_session(session_dir)

        self.assertTrue(detail["readable"])
        self.assertEqual(detail["availability"]["manifest"], "malformed")
        self.assertEqual(detail["availability"]["changes"], "malformed")
        self.assertIsNone(detail["artifacts"]["manifest"])
        self.assertIsNone(detail["artifacts"]["changes"])

    def test_list_agent_sessions_skips_crashing_on_unreadable_json_artifacts(self) -> None:
        session_dir = self._write_session("listed-unreadable-json")
        (session_dir / "trace-summary.json").write_bytes(b'{"tool_call_count": "\xff"}')

        sessions = list_agent_sessions(self.runs_dir)

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "listed-unreadable-json")

    def test_read_agent_session_marks_existing_unreadable_text_artifacts_malformed(self) -> None:
        session_dir = self._write_session("unreadable-text")
        (session_dir / "events.jsonl").unlink()
        (session_dir / "events.jsonl").mkdir()
        (session_dir / "transcript.txt").unlink()
        (session_dir / "transcript.txt").mkdir()

        detail = read_agent_session(session_dir)

        self.assertTrue(detail["readable"])
        self.assertEqual(detail["availability"]["events"], "malformed")
        self.assertEqual(detail["availability"]["transcript"], "malformed")
        self.assertEqual(detail["timeline"]["events"], [])
        self.assertEqual(detail["timeline"]["raw"], "")
        self.assertEqual(detail["artifacts"]["transcript"], "")

    def test_list_agent_sessions_skips_escaped_resolved_session_dirs(self) -> None:
        import os
        import subprocess

        inside = self._write_session("inside")
        outside = self.temp_dir / "outside-session"
        outside.mkdir()
        self._write_json(
            outside / "result.json",
            {
                "session_id": "outside-leak",
                "session_type": "suite-agent-session",
                "contract_version": 1,
                "backend": "command",
                "status": "passed",
            },
        )
        link = self.runs_dir / "escaped"

        if os.name == "nt":
            completed = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                text=True,
                encoding="utf-8",
                capture_output=True,
            )
            if completed.returncode != 0:
                self.skipTest(f"junction creation unavailable: {completed.stderr or completed.stdout}")
        else:
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

        import time

        newer_time = time.time() + 10
        os.utime(outside / "result.json", (newer_time, newer_time))
        os.utime(inside / "result.json", (1, 1))

        sessions = list_agent_sessions(self.runs_dir)

        self.assertEqual([item["session_id"] for item in sessions], ["inside"])

    def test_read_agent_session_live_marks_running_session(self) -> None:
        now = datetime(2026, 5, 27, 12, 0, 0)
        session_dir = self._write_running_session(
            "live-running",
            start_time=now - timedelta(seconds=30),
            last_event_time=now - timedelta(seconds=10),
        )

        live = read_agent_session_live(session_dir, now=now)

        self.assertEqual(live["session_id"], "live-running")
        self.assertEqual(live["lifecycle"], "running")
        self.assertEqual(live["elapsed_seconds"], 30.0)
        self.assertEqual(live["event_count"], 2)
        self.assertEqual(live["last_event"]["event"], "output")
        self.assertEqual(live["output_bytes"], 29)
        self.assertEqual(live["last_output_preview"], "latest child output")
        self.assertIn("latest child output", live["transcript_tail"])

    def test_read_agent_session_live_marks_stale_running_session(self) -> None:
        now = datetime(2026, 5, 27, 12, 0, 0)
        old_activity = now - timedelta(seconds=LIVE_STALE_AFTER_SECONDS + 5)
        session_dir = self._write_running_session(
            "live-stale",
            start_time=old_activity - timedelta(seconds=10),
            last_event_time=old_activity,
        )

        live = read_agent_session_live(session_dir, now=now)

        self.assertEqual(live["lifecycle"], "stale")
        self.assertEqual(live["stale_after_seconds"], LIVE_STALE_AFTER_SECONDS)

    def test_read_agent_session_live_marks_malformed_result_unreadable(self) -> None:
        now = datetime(2026, 5, 27, 12, 0, 0)
        session_dir = self._write_running_session(
            "live-malformed-result",
            start_time=now - timedelta(seconds=30),
            last_event_time=now - timedelta(seconds=10),
        )
        (session_dir / "result.json").write_text("{bad json\n", encoding="utf-8")

        live = read_agent_session_live(session_dir, now=now)

        self.assertEqual(live["lifecycle"], "unreadable")
        self.assertFalse(live["result_available"])

    def test_read_agent_session_live_preserves_completed_status(self) -> None:
        session_dir = self._write_session("live-complete")

        live = read_agent_session_live(session_dir, now=datetime(2026, 5, 27, 12, 0, 0))

        self.assertEqual(live["lifecycle"], "passed")
        self.assertEqual(live["elapsed_seconds"], 1.25)
        self.assertEqual(live["event_count"], 2)
        self.assertEqual(live["last_event"]["type"], "finish")
        self.assertIn("Hello from child.", live["transcript_tail"])

    def test_summarize_live_sessions_reports_counts_and_recommendation(self) -> None:
        now = datetime(2026, 5, 27, 12, 0, 0)
        self._write_running_session(
            "live-running-summary",
            start_time=now - timedelta(seconds=40),
            last_event_time=now - timedelta(seconds=5),
        )
        completed = self._write_session("live-completed-summary")
        result = json.loads((completed / "result.json").read_text(encoding="utf-8"))
        result["duration_seconds"] = 600
        self._write_json(completed / "result.json", result)

        summary = summarize_live_sessions(self.runs_dir, now=now)

        self.assertEqual(summary["active_count"], 1)
        self.assertEqual(summary["stale_count"], 0)
        self.assertEqual(summary["completed_count"], 1)
        self.assertEqual(summary["average_completed_duration_seconds"], 600.0)
        self.assertEqual(summary["slowest_sessions"][0]["session_id"], "live-completed-summary")
        self.assertGreaterEqual(summary["recommended_loop_interval_minutes"], 20)

    def test_summarize_live_sessions_uses_injected_now_for_live_state(self) -> None:
        now = datetime(2020, 1, 1, 12, 0, 0)
        self._write_running_session(
            "live-fixed-now-summary",
            start_time=now - timedelta(seconds=40),
            last_event_time=now - timedelta(seconds=5),
        )

        summary = summarize_live_sessions(self.runs_dir, now=now)

        self.assertEqual(summary["active_count"], 1)
        self.assertEqual(summary["stale_count"], 0)

    def _request_viewer_json(self, path: str) -> tuple[int, dict]:
        import http.client
        import threading
        from http.server import ThreadingHTTPServer

        from suite.agent_viewer import make_agent_viewer_handler

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_agent_viewer_handler(self.runs_dir))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            try:
                connection.request("GET", path)
                response = connection.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
                return response.status, payload
            finally:
                connection.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_make_agent_viewer_handler_serves_session_list(self) -> None:
        self._write_session("api-session", backend="pi", include_pi=True)

        status, payload = self._request_viewer_json("/api/sessions")

        self.assertEqual(status, 200)
        self.assertEqual(payload["sessions"][0]["session_id"], "api-session")

    def test_make_agent_viewer_handler_serves_session_detail(self) -> None:
        self._write_session("api-detail", backend="pi", include_pi=True)

        status, payload = self._request_viewer_json("/api/sessions/api-detail")

        self.assertEqual(status, 200)
        self.assertEqual(payload["session"]["session_id"], "api-detail")
        self.assertEqual(payload["session"]["backend"], "pi")
        self.assertEqual(payload["session"]["model"], "gemini-2.5-flash-lite")

    def test_make_agent_viewer_handler_blocks_path_traversal(self) -> None:
        status, payload = self._request_viewer_json("/api/sessions/..%2FAGENTS.md")

        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "session not found")

    def test_make_agent_viewer_handler_serves_live_session_list(self) -> None:
        now = datetime.now()
        self._write_running_session(
            "api-live-running",
            start_time=now - timedelta(seconds=20),
            last_event_time=now - timedelta(seconds=2),
        )

        status, payload = self._request_viewer_json("/api/sessions?include_live=1")

        self.assertEqual(status, 200)
        self.assertEqual(payload["sessions"][0]["session_id"], "api-live-running")
        self.assertIn("live", payload["sessions"][0])
        self.assertEqual(payload["sessions"][0]["live"]["lifecycle"], "running")

    def test_make_agent_viewer_handler_serves_live_session_detail(self) -> None:
        now = datetime.now()
        self._write_running_session(
            "api-live-detail",
            start_time=now - timedelta(seconds=20),
            last_event_time=now - timedelta(seconds=2),
        )

        status, payload = self._request_viewer_json("/api/sessions/api-live-detail/live")

        self.assertEqual(status, 200)
        self.assertEqual(payload["live"]["session_id"], "api-live-detail")
        self.assertEqual(payload["live"]["lifecycle"], "running")

    def test_make_agent_viewer_handler_serves_live_summary(self) -> None:
        now = datetime.now()
        self._write_running_session(
            "api-live-summary",
            start_time=now - timedelta(seconds=20),
            last_event_time=now - timedelta(seconds=2),
        )

        status, payload = self._request_viewer_json("/api/live-summary")

        self.assertEqual(status, 200)
        self.assertEqual(payload["summary"]["active_count"], 1)
        self.assertIn("recommended_loop_interval_minutes", payload["summary"])

    def test_agent_viewer_cli_help_lists_viewer_command(self) -> None:
        import subprocess
        import sys

        completed = subprocess.run(
            [sys.executable, "-m", "suite.cli", "agent", "viewer", "--help"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("--agent-runs-dir", completed.stdout)
        self.assertIn("--port", completed.stdout)
