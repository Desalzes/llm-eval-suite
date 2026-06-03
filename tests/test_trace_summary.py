import unittest

from suite.trace_summary import build_trace_summary


class TraceSummaryTests(unittest.TestCase):
    def test_build_trace_summary_extracts_agent_signals(self) -> None:
        transcript = """=== child output ===
OpenAI Codex v0.130.0
--------
workdir: C:\\Users\\desal\\ChatGPT
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write
reasoning effort: xhigh
session id: 019e1965-0c19
--------
exec
"python" "-m" "unittest" "discover"
Using superpowers:test-driven-development to guide the fix.
ERROR one transient command failed
tokens used
1,234
"""

        summary = build_trace_summary(transcript)

        self.assertEqual(summary["model"], "gpt-5.5")
        self.assertEqual(summary["provider"], "openai")
        self.assertEqual(summary["child_session_id"], "019e1965-0c19")
        self.assertEqual(summary["tool_call_count"], 1)
        self.assertTrue(summary["mentions_tests"])
        self.assertTrue(summary["mentions_skills"])
        self.assertEqual(summary["error_marker_count"], 1)
        self.assertEqual(summary["tokens_used"], 1234)

    def test_build_trace_summary_reports_runtime_noise_and_retry_markers(self) -> None:
        transcript = """=== child output ===
2026-05-14T16:36:37.082049Z  WARN codex_core_plugins::startup_remote_sync: remote plugin sync request failed
<html>challenge page</html>
2026-05-14T16:36:37.087768Z  WARN codex_core_plugins::manager: failed to warm featured plugin ids cache
OpenAI Codex v0.130.0
--------
model: gpt-5.5
--------
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content -LiteralPath 'C:\\Users\\desal\\.codex\\plugins\\cache\\openai-curated\\superpowers\\7955f1db\\skills\\test-driven-development\\SKILL.md' -Raw"
apply patch
============================= test session starts =============================
FAILED tests/test_pause_policy.py::test_before_cutoff
apply patch
============================= test session starts =============================
tokens used
42,000
"""

        summary = build_trace_summary(transcript)

        self.assertEqual(summary["startup_warning_count"], 2)
        self.assertEqual(summary["remote_plugin_sync_warning_count"], 1)
        self.assertGreater(summary["startup_preamble_bytes"], 0)
        self.assertEqual(summary["skill_file_read_count"], 1)
        self.assertEqual(summary["patch_attempt_count"], 2)
        self.assertEqual(summary["pytest_session_count"], 2)
        self.assertEqual(summary["pytest_failed_test_marker_count"], 1)


if __name__ == "__main__":
    unittest.main()
