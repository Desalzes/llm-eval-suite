import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write_fake_codex(bin_dir: Path) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_codex = bin_dir / "codex.cmd"
    fake_codex.write_text(
        "\n".join(
            [
                "@echo off",
                'if exist "%CODEX_ARG_CAPTURE%" del "%CODEX_ARG_CAPTURE%"',
                ":loop",
                'if "%~1"=="" goto done',
                '>> "%CODEX_ARG_CAPTURE%" echo [%~1]',
                "shift",
                "goto loop",
                ":done",
                '>> "%CODEX_ARG_CAPTURE%" echo ENV:%CODEX_WRAPPER_TEST_TOKEN%',
                '>> "%CODEX_ARG_CAPTURE%" echo HOME:%CODEX_HOME%',
                "exit /b 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return fake_codex


class CodexAgentWrapperTests(unittest.TestCase):
    def test_windows_launcher_resolves_codex_via_path_and_pins_codex_home(self) -> None:
        launcher = _read("scripts/codex-agent.cmd")

        self.assertIn("CODEX_BIN", launcher)
        self.assertIn("codex.cmd", launcher)
        self.assertIn("CODEX_HOME", launcher)
        self.assertIn("local\\codex-home", launcher)
        self.assertIn("local\\codex.env", launcher)
        self.assertIn("%*", launcher)

    def test_windows_launcher_runs_real_codex_with_version_flag(self) -> None:
        launcher = ROOT / "scripts" / "codex-agent.cmd"

        result = subprocess.run(
            [str(launcher), "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("codex", output.lower())

    def test_windows_launcher_forwards_quoted_args_through_fake_codex(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-wrapper-args-test-") as temp:
            temp_root = Path(temp)
            scripts_dir = temp_root / "scripts"
            scripts_dir.mkdir()
            shutil.copy(ROOT / "scripts" / "codex-agent.cmd", scripts_dir / "codex-agent.cmd")

            fake_bin = temp_root / "fakebin"
            capture_path = temp_root / "captured-args.txt"
            fake_codex = _write_fake_codex(fake_bin)

            env = dict(os.environ)
            env["CODEX_BIN"] = str(fake_codex)
            env["CODEX_ARG_CAPTURE"] = str(capture_path)
            result = subprocess.run(
                [
                    str(scripts_dir / "codex-agent.cmd"),
                    "exec",
                    "-p",
                    "Reply exactly: codex cmd smoke ok",
                    "-C",
                    str(temp_root),
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
            self.assertIn("[exec]", captured)
            self.assertIn("[-p]", captured)
            self.assertIn("[Reply exactly: codex cmd smoke ok]", captured)
            self.assertIn("[-C]", captured)
            self.assertNotIn("[Reply]", captured)

    def test_windows_launcher_loads_local_codex_env_before_running_codex(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-wrapper-env-test-") as temp:
            temp_root = Path(temp)
            scripts_dir = temp_root / "scripts"
            local_dir = temp_root / "local"
            scripts_dir.mkdir()
            local_dir.mkdir()
            shutil.copy(ROOT / "scripts" / "codex-agent.cmd", scripts_dir / "codex-agent.cmd")

            fake_bin = temp_root / "fakebin"
            capture_path = temp_root / "captured-env.txt"
            fake_codex = _write_fake_codex(fake_bin)
            (local_dir / "codex.env").write_text(
                "CODEX_WRAPPER_TEST_TOKEN=from-local-env\n",
                encoding="utf-8",
            )

            env = dict(os.environ)
            env.pop("CODEX_WRAPPER_TEST_TOKEN", None)
            env["CODEX_BIN"] = str(fake_codex)
            env["CODEX_ARG_CAPTURE"] = str(capture_path)
            result = subprocess.run(
                [str(scripts_dir / "codex-agent.cmd"), "--version"],
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

    def test_windows_launcher_defaults_codex_home_into_repo_local_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-wrapper-home-test-") as temp:
            temp_root = Path(temp)
            scripts_dir = temp_root / "scripts"
            scripts_dir.mkdir()
            shutil.copy(ROOT / "scripts" / "codex-agent.cmd", scripts_dir / "codex-agent.cmd")

            fake_bin = temp_root / "fakebin"
            capture_path = temp_root / "captured-home.txt"
            fake_codex = _write_fake_codex(fake_bin)

            env = dict(os.environ)
            env.pop("CODEX_HOME", None)
            env["CODEX_BIN"] = str(fake_codex)
            env["CODEX_ARG_CAPTURE"] = str(capture_path)
            result = subprocess.run(
                [str(scripts_dir / "codex-agent.cmd"), "--version"],
                cwd=temp_root,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )

            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            captured = capture_path.read_text(encoding="utf-8").splitlines()
            expected_home = str(temp_root / "local" / "codex-home")
            self.assertIn(f"HOME:{expected_home}", captured)
            self.assertTrue((temp_root / "local" / "codex-home").exists())

    def test_no_skills_launcher_uses_isolated_codex_home_with_global_auth_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-no-skills-wrapper-test-") as temp:
            temp_root = Path(temp)
            scripts_dir = temp_root / "scripts"
            scripts_dir.mkdir()
            shutil.copy(
                ROOT / "scripts" / "codex-global-no-skills.cmd",
                scripts_dir / "codex-global-no-skills.cmd",
            )

            fake_profile = temp_root / "fake-user"
            fake_global_home = fake_profile / ".codex"
            fake_global_home.mkdir(parents=True)
            (fake_global_home / "auth.json").write_text('{"OPENAI_API_KEY":"test"}\n', encoding="utf-8")
            (fake_global_home / "skills").mkdir()

            fake_bin = temp_root / "fakebin"
            capture_path = temp_root / "captured-no-skills-home.txt"
            fake_codex = _write_fake_codex(fake_bin)

            env = dict(os.environ)
            env.pop("CODEX_HOME", None)
            env["USERPROFILE"] = str(fake_profile)
            env["CODEX_BIN"] = str(fake_codex)
            env["CODEX_ARG_CAPTURE"] = str(capture_path)
            result = subprocess.run(
                [str(scripts_dir / "codex-global-no-skills.cmd"), "--version"],
                cwd=temp_root,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )

            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            control_home = temp_root / "local" / "codex-no-skills-home"
            captured = capture_path.read_text(encoding="utf-8").splitlines()
            self.assertIn(f"HOME:{control_home}", captured)
            self.assertTrue((control_home / "auth.json").exists())
            self.assertFalse((control_home / "skills").exists())
