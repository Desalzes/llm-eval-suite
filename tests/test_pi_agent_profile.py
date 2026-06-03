import unittest
from pathlib import Path

from suite.models import load_profile


ROOT = Path(__file__).resolve().parents[1]


class PiAgentProfileTests(unittest.TestCase):
    def test_pi_google_readonly_profile_uses_windows_wrapper_and_prompt_file(self) -> None:
        profile = load_profile(ROOT / "profiles" / "pi-google-readonly.json")

        self.assertEqual(profile.id, "pi-google-readonly")
        self.assertEqual(profile.command[0], "scripts\\pi-agent.cmd")
        self.assertIn("--provider", profile.command)
        self.assertIn("google", profile.command)
        self.assertIn("--model", profile.command)
        self.assertIn("gemini-2.5-flash-lite", profile.command)
        self.assertIn("--tools", profile.command)
        self.assertIn("read,grep,find,ls", profile.command)
        self.assertIn("-p", profile.command)
        self.assertIn("@{prompt_file}", profile.command)

    def test_readme_documents_supervised_pi_readonly_smoke(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        section = readme.split("## Supervise A Terminal Session", 1)[1].split("\n## ", 1)[0]

        self.assertIn("--profile profiles/pi-google-readonly.json", section)
        self.assertIn("--allowed-path local/pi-sessions/*", section)
        self.assertIn("--timeout-seconds 120", section)

    def test_project_policy_names_readonly_pi_profile_for_bounded_delegation(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("profiles/pi-google-readonly.json", agents)
        self.assertIn("local/pi-sessions/*", agents)
