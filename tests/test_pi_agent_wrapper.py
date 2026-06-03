import os
import unittest
import subprocess
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write_fake_pi(repo_root: Path, capture_path: Path) -> None:
    pi_bin_dir = repo_root / "node_modules" / ".bin"
    pi_bin_dir.mkdir(parents=True)
    fake_pi = pi_bin_dir / "pi.cmd"
    fake_pi.write_text(
        "\n".join(
            [
                "@echo off",
                'if exist "%PI_ARG_CAPTURE%" del "%PI_ARG_CAPTURE%"',
                ":loop",
                'if "%~1"=="" goto done',
                '>> "%PI_ARG_CAPTURE%" echo [%~1]',
                "shift",
                "goto loop",
                ":done",
                '>> "%PI_ARG_CAPTURE%" echo ENV:%PI_WRAPPER_TEST_TOKEN%',
                "exit /b 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class PiAgentWrapperTests(unittest.TestCase):
    def test_windows_launcher_uses_repo_pinned_pi_and_local_session_dir(self) -> None:
        launcher = _read("scripts/pi-agent.cmd")

        self.assertIn("node_modules\\.bin\\pi.cmd", launcher)
        self.assertIn("--session-dir", launcher)
        self.assertIn("local\\pi-sessions", launcher)
        self.assertIn("local\\pi.env", launcher)
        self.assertIn("%*", launcher)

    def test_windows_launcher_forwards_pi_flags_that_start_with_dash(self) -> None:
        launcher = ROOT / "scripts" / "pi-agent.cmd"

        result = subprocess.run(
            [str(launcher), "--no-tools", "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertRegex(output, r"\d+\.\d+\.\d+")

    def test_windows_launcher_does_not_parse_pi_print_flag_as_powershell_arg(self) -> None:
        launcher = ROOT / "scripts" / "pi-agent.cmd"

        result = subprocess.run(
            [
                str(launcher),
                "--api-key",
                "sentinel",
                "-p",
                "Reply exactly: pi cmd smoke ok",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        self.assertNotIn("A parameter cannot be found", output)
        self.assertIn("--api-key requires a model", output)

    def test_windows_launcher_preserves_quoted_prompt_as_one_pi_argument(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pi-wrapper-test-") as temp:
            temp_root = Path(temp)
            scripts_dir = temp_root / "scripts"
            scripts_dir.mkdir()
            shutil.copy(ROOT / "scripts" / "pi-agent.cmd", scripts_dir / "pi-agent.cmd")
            shutil.copy(ROOT / "scripts" / "pi-agent.ps1", scripts_dir / "pi-agent.ps1")

            capture_path = temp_root / "captured-args.txt"
            _write_fake_pi(temp_root, capture_path)

            env = dict(**os.environ, PI_ARG_CAPTURE=str(capture_path))
            result = subprocess.run(
                [
                    str(scripts_dir / "pi-agent.cmd"),
                    "--provider",
                    "google",
                    "--no-tools",
                    "-p",
                    "Reply exactly: pi cmd smoke ok",
                ],
                cwd=temp_root,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )

            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            captured = capture_path.read_text(encoding="utf-8").splitlines()
            self.assertIn("[-p]", captured)
            self.assertIn("[Reply exactly: pi cmd smoke ok]", captured)
            self.assertNotIn("[Reply]", captured)

    def test_windows_launcher_loads_local_pi_env_before_running_pi(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pi-wrapper-env-test-") as temp:
            temp_root = Path(temp)
            scripts_dir = temp_root / "scripts"
            local_dir = temp_root / "local"
            scripts_dir.mkdir()
            local_dir.mkdir()
            shutil.copy(ROOT / "scripts" / "pi-agent.cmd", scripts_dir / "pi-agent.cmd")

            capture_path = temp_root / "captured-env.txt"
            _write_fake_pi(temp_root, capture_path)
            (local_dir / "pi.env").write_text(
                "PI_WRAPPER_TEST_TOKEN=from-local-env\n",
                encoding="utf-8",
            )

            env = dict(os.environ)
            env.pop("PI_WRAPPER_TEST_TOKEN", None)
            env["PI_ARG_CAPTURE"] = str(capture_path)
            result = subprocess.run(
                [str(scripts_dir / "pi-agent.cmd"), "--version"],
                cwd=temp_root,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )

            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            captured = capture_path.read_text(encoding="utf-8").splitlines()
            self.assertIn("ENV:from-local-env", captured)

    def test_docs_use_cmd_launcher_for_windows_examples(self) -> None:
        readme = _read("README.md")
        section = readme.split("## Run Pi Agents", 1)[1].split("\n## ", 1)[0]

        self.assertIn(".\\scripts\\pi-agent.cmd --help", section)
        self.assertIn(".\\scripts\\pi-agent.cmd --tools read,grep,find,ls", section)
        self.assertIn(".\\scripts\\pi-agent.cmd --provider openai", section)
        self.assertNotIn(".\\scripts\\pi-agent.ps1 --", section)

    def test_project_policy_points_master_delegation_at_windows_safe_launcher(self) -> None:
        agents = _read("AGENTS.md")

        self.assertIn("scripts/pi-agent.cmd", agents)
        self.assertIn("local/pi-sessions", agents)
