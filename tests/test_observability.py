import unittest

from suite.observability import build_observability_summary, format_observability_markdown


class ObservabilityTests(unittest.TestCase):
    def test_summary_marks_clean_runs_and_surfaces_hotspots(self) -> None:
        summary = build_observability_summary(
            {
                "pass_rate": 1.0,
                "unsafe_rate": 0.0,
                "timeout_rate": 0.0,
                "cap_reason_counts": {},
                "runs_missing_tokens": 0,
                "runs_missing_runtime": 0,
                "average_runtime_per_task_seconds": 7.625,
                "per_task": {
                    "fast": {
                        "average_runtime_per_task_seconds": 2.0,
                        "total_child_runtime_seconds": 4.0,
                        "total_tokens": 50,
                        "total_tool_calls": 3,
                        "status_counts": {"passed": 2},
                    },
                    "slow": {
                        "average_runtime_per_task_seconds": 12.0,
                        "total_child_runtime_seconds": 24.0,
                        "total_tokens": 150,
                        "total_tool_calls": 2,
                        "status_counts": {"passed": 2},
                    },
                    "tool-heavy": {
                        "average_runtime_per_task_seconds": 5.0,
                        "total_child_runtime_seconds": 10.0,
                        "total_tokens": 75,
                        "total_tool_calls": 12,
                        "status_counts": {"passed": 2},
                    },
                },
            }
        )

        self.assertEqual(summary["health"], "clean")
        self.assertEqual(summary["risk_flags"], [])
        self.assertEqual(summary["runtime_hotspots"][0]["task_id"], "slow")
        self.assertEqual(summary["token_hotspots"][0]["task_id"], "slow")
        self.assertEqual(summary["tool_hotspots"][0]["task_id"], "tool-heavy")
        self.assertEqual(summary["tool_hotspots"][0]["total_tool_calls"], 12)
        self.assertEqual(summary["missing_data"], {"tokens": 0, "runtime": 0})
        self.assertEqual(
            summary["recommendations"],
            [
                {
                    "kind": "runtime_hotspot",
                    "task_id": "slow",
                    "reason": "Average runtime 12.0s is 1.57x the set average.",
                    "action": "Keep this task out of smoke checks unless its coverage justifies the added wait, or tighten the fixture before promoting frequent runs.",
                }
            ],
        )

    def test_summary_marks_attention_for_failures_caps_and_missing_data(self) -> None:
        summary = build_observability_summary(
            {
                "pass_rate": 0.5,
                "unsafe_rate": 0.25,
                "timeout_rate": 0.25,
                "status_counts": {"passed": 2, "failed": 1, "unsafe": 1},
                "cap_reason_counts": {"timeout_seconds": 1},
                "runs_missing_tokens": 1,
                "runs_missing_runtime": 2,
                "per_task": {},
            }
        )

        self.assertEqual(summary["health"], "attention")
        self.assertEqual(summary["failure_status_counts"], {"failed": 1, "unsafe": 1})
        self.assertEqual(summary["missing_data"], {"tokens": 1, "runtime": 2})
        self.assertIn("non_passing_runs", summary["risk_flags"])
        self.assertIn("unsafe_runs", summary["risk_flags"])
        self.assertIn("timeouts", summary["risk_flags"])
        self.assertIn("caps_triggered", summary["risk_flags"])
        self.assertIn("missing_trace_data", summary["risk_flags"])

    def test_markdown_lists_recommendation_details(self) -> None:
        markdown = format_observability_markdown(
            {
                "health": "clean",
                "risk_flags": [],
                "missing_data": {"tokens": 0, "runtime": 0},
                "recommendations": [
                    {
                        "kind": "runtime_hotspot",
                        "task_id": "skill-script-preservation",
                        "reason": "Average runtime 213.171s is 1.53x the set average.",
                        "action": "Keep this task out of smoke checks unless its coverage justifies the added wait.",
                    }
                ],
                "runtime_hotspots": [],
                "token_hotspots": [],
                "tool_hotspots": [
                    {
                        "task_id": "tool-heavy",
                        "average_runtime_per_task_seconds": 5.0,
                        "total_child_runtime_seconds": 10.0,
                        "total_tokens": 75,
                        "total_tool_calls": 12,
                        "status_counts": {"passed": 2},
                    }
                ],
            }
        )

        self.assertIn("### Recommendations", markdown)
        self.assertIn("| runtime_hotspot | skill-script-preservation |", markdown)
        self.assertIn("Average runtime 213.171s is 1.53x the set average.", markdown)
        self.assertIn("Keep this task out of smoke checks", markdown)
        self.assertIn("### Tool Hotspots", markdown)
        self.assertIn("| tool-heavy | 5.0 | 10.0 | 75 | 12 | `{'passed': 2}` |", markdown)


if __name__ == "__main__":
    unittest.main()
