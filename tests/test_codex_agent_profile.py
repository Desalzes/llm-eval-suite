import unittest
from pathlib import Path

from suite.models import load_profile


ROOT = Path(__file__).resolve().parents[1]


class CodexAgentProfileTests(unittest.TestCase):
    def test_codex_baseline_profile_uses_windows_wrapper(self) -> None:
        profile = load_profile(ROOT / "profiles" / "codex-baseline.json")

        self.assertEqual(profile.id, "codex-baseline")
        self.assertEqual(profile.command[0], "{suite_root}\\scripts\\codex-agent.cmd")
        self.assertIn("exec", profile.command)
        self.assertIn("--skip-git-repo-check", profile.command)
        self.assertIn("-s", profile.command)
        self.assertIn("danger-full-access", profile.command)
        self.assertIn("model_reasoning_effort=\"none\"", profile.command)
        self.assertIn("-C", profile.command)
        self.assertIn("{workspace}", profile.command)

    def test_codex_wrapped_baseline_profile_uses_windows_wrapper(self) -> None:
        profile = load_profile(ROOT / "profiles" / "codex-wrapped-baseline.json")

        self.assertEqual(profile.id, "codex-wrapped-baseline")
        self.assertEqual(profile.command[0], "{suite_root}\\scripts\\codex-agent.cmd")
        self.assertIn("exec", profile.command)
        self.assertIn("--skip-git-repo-check", profile.command)
        self.assertIn("-s", profile.command)
        self.assertIn("danger-full-access", profile.command)
        self.assertIn("model_reasoning_effort=\"none\"", profile.command)
        self.assertIn("-C", profile.command)
        self.assertIn("{workspace}", profile.command)

    def test_codex_global_no_skills_profile_uses_control_wrapper(self) -> None:
        profile = load_profile(ROOT / "profiles" / "codex-global-no-skills.json")

        self.assertEqual(profile.id, "codex-global-no-skills")
        self.assertEqual(profile.command[0], "{suite_root}\\scripts\\codex-global-no-skills.cmd")
        self.assertIn("exec", profile.command)
        self.assertIn("--skip-git-repo-check", profile.command)
        self.assertIn("--ignore-user-config", profile.command)
        self.assertIn("-s", profile.command)
        self.assertIn("danger-full-access", profile.command)
        self.assertIn("model_reasoning_effort=\"none\"", profile.command)
        self.assertIn("-C", profile.command)
        self.assertIn("{workspace}", profile.command)
