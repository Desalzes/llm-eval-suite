import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from suite.git_utils import changed_files, run_git


class GitUtilsTests(unittest.TestCase):
    def test_changed_files_ignores_non_porcelain_warning_lines(self) -> None:
        git_result = subprocess.CompletedProcess(
            ["git", "status", "--porcelain"],
            0,
            stdout=(
                " M src/app.py\n"
                "warning: could not open directory '.pytest_cache/': Permission denied\n"
                "?? notes.txt\n"
            ),
            stderr="",
        )

        with patch("suite.git_utils.run_git", return_value=git_result):
            self.assertEqual(changed_files(Path(".")), ["notes.txt", "src/app.py"])

    def test_changed_files_ignores_pytest_runtime_artifacts(self) -> None:
        git_result = subprocess.CompletedProcess(
            ["git", "status", "--porcelain"],
            0,
            stdout=(
                "?? .pytest-tmp/pytest-of-desal/test_example0/output.txt\n"
                "?? .pytest_cache/v/cache/nodeids\n"
                "?? src/app.py\n"
            ),
            stderr="",
        )

        with patch("suite.git_utils.run_git", return_value=git_result):
            self.assertEqual(changed_files(Path(".")), ["src/app.py"])

    def test_changed_files_expands_untracked_directories_to_files(self) -> None:
        status_result = subprocess.CompletedProcess(
            ["git", "status", "--porcelain"],
            0,
            stdout="?? skills/browser-testing/references/\n",
            stderr="",
        )
        ls_files_result = subprocess.CompletedProcess(
            ["git", "ls-files"],
            0,
            stdout="skills/browser-testing/references/playwright.md\n",
            stderr="",
        )

        with patch("suite.git_utils.run_git", side_effect=[status_result, ls_files_result]):
            self.assertEqual(
                changed_files(Path(".")),
                ["skills/browser-testing/references/playwright.md"],
            )

    def test_run_git_captures_stderr_separately_from_parseable_stdout(self) -> None:
        with patch("suite.git_utils.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(["git"], 0, stdout="", stderr="warning")

            result = run_git(["status", "--porcelain"], Path("."))

        self.assertEqual(result.stderr, "warning")
        self.assertEqual(run.call_args.kwargs["stderr"], subprocess.PIPE)


if __name__ == "__main__":
    unittest.main()
