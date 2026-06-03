import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.models import TaskSpec, load_profile, load_task
from suite.improvement import run_improvement_cycle
from suite.fixture_loop import load_inbox_candidates, run_fixture_loop
from suite.runner import _copy_workspace, _retry_path_operation, run_suite_iterations, run_suite_task


ROOT = Path(__file__).resolve().parents[1]


class SuiteRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="suite-runner-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_loads_task_and_profile_json(self) -> None:
        task = load_task(ROOT / "tasks/examples/python-cli-bugfix/task.json")
        profile = load_profile(ROOT / "profiles/noop.json")

        self.assertEqual(task.id, "python-cli-bugfix")
        self.assertEqual(task.allowed_paths, ["calculator.py"])
        self.assertEqual(profile.id, "noop")
        self.assertIn("{prompt_file}", profile.command)

    def test_noop_run_captures_failed_tests_without_harness_failure(self) -> None:
        result = run_suite_task(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=ROOT / "profiles/noop.json",
            run_id="unit-noop",
            runs_dir=self.temp_dir,
            force=True,
        )

        run_dir = self.temp_dir / "unit-noop"
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["agent_exit_code"], 0)
        self.assertNotEqual(result["test_exit_code"], 0)
        self.assertFalse(result["tests_passed"])
        self.assertEqual(result["changed_files"], [])
        self.assertTrue((run_dir / "manifest.json").exists())
        self.assertTrue((run_dir / "prompt.md").exists())
        self.assertTrue((run_dir / "agent-output.txt").exists())
        self.assertTrue((run_dir / "test-output.txt").exists())
        self.assertTrue((run_dir / "diff.patch").exists())
        self.assertTrue((run_dir / "result.json").exists())
        self.assertTrue((run_dir / "review.md").exists())

        persisted = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted["status"], "failed")

    def test_forbidden_changes_are_scored_unsafe(self) -> None:
        profile_path = self.temp_dir / "unsafe-profile.json"
        profile_path.write_text(
            json.dumps(
                {
                    "id": "unsafe-writer",
                    "name": "Unsafe Writer",
                    "description": "Writes outside the allowed path set.",
                    "command": [
                        "python",
                        "-c",
                        "from pathlib import Path; Path('notes.txt').write_text('unsafe', encoding='utf-8')",
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = run_suite_task(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=profile_path,
            run_id="unit-unsafe",
            runs_dir=self.temp_dir,
            force=True,
        )

        self.assertEqual(result["status"], "unsafe")
        self.assertIn("notes.txt", result["changed_files"])
        self.assertIn("notes.txt", result["forbidden_changed_files"])

    def test_force_removes_existing_read_only_run_directory(self) -> None:
        run_dir = self.temp_dir / "unit-readonly"
        read_only_file = run_dir / "workspace" / ".git" / "objects" / "readonly"
        read_only_file.parent.mkdir(parents=True)
        read_only_file.write_text("locked", encoding="utf-8")
        read_only_file.chmod(stat.S_IREAD)
        self.addCleanup(lambda: os.chmod(read_only_file, stat.S_IWRITE) if read_only_file.exists() else None)

        result = run_suite_task(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=ROOT / "profiles/noop.json",
            run_id="unit-readonly",
            runs_dir=self.temp_dir,
            force=True,
        )

        self.assertEqual(result["status"], "failed")
        self.assertTrue((run_dir / "result.json").exists())

    def test_retry_path_operation_handles_transient_permission_errors(self) -> None:
        attempts: list[str] = []

        def flaky_remove(path: str) -> None:
            attempts.append(path)
            if len(attempts) < 3:
                raise PermissionError("path is temporarily locked")

        _retry_path_operation(flaky_remove, "locked-path", attempts=5, delay_seconds=0)

        self.assertEqual(attempts, ["locked-path", "locked-path", "locked-path"])

    def test_copy_workspace_ignores_pytest_cache(self) -> None:
        repo = self.temp_dir / "repo-with-cache"
        repo.mkdir()
        (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (repo / ".pytest_cache").mkdir()
        (repo / ".pytest_cache" / "README.md").write_text("cache", encoding="utf-8")
        (repo / ".pytest-tmp").mkdir()
        (repo / ".pytest-tmp" / "leftover.txt").write_text("cache", encoding="utf-8")
        (repo / "pytest-cache-files-leftover").mkdir()
        (repo / "pytest-cache-files-leftover" / "nodeids").write_text("cache", encoding="utf-8")
        task = TaskSpec(
            id="cache-fixture",
            title="Cache Fixture",
            description="Fixture with pytest cache.",
            path=self.temp_dir / "task.json",
            repo=repo,
            test_command=["python"],
            allowed_paths=["app.py"],
            success_criteria=[],
        )

        workspace = self.temp_dir / "workspace"
        _copy_workspace(task, workspace)

        self.assertTrue((workspace / "app.py").exists())
        self.assertFalse((workspace / ".pytest_cache").exists())
        self.assertFalse((workspace / ".pytest-tmp").exists())
        self.assertFalse((workspace / "pytest-cache-files-leftover").exists())

    def test_iterations_create_numbered_runs_and_summary(self) -> None:
        summary = run_suite_iterations(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=ROOT / "profiles/noop.json",
            iterations=3,
            run_id_base="unit-loop",
            runs_dir=self.temp_dir,
            force=True,
        )

        self.assertEqual(summary["run_id_base"], "unit-loop")
        self.assertEqual(summary["iterations"], 3)
        self.assertEqual(summary["status_counts"], {"failed": 3})
        self.assertEqual([run["run_id"] for run in summary["runs"]], ["unit-loop-01", "unit-loop-02", "unit-loop-03"])
        self.assertTrue((self.temp_dir / "unit-loop-01" / "result.json").exists())
        self.assertTrue((self.temp_dir / "unit-loop-02" / "result.json").exists())
        self.assertTrue((self.temp_dir / "unit-loop-03" / "result.json").exists())
        self.assertTrue((self.temp_dir / "unit-loop-summary.json").exists())
        self.assertTrue((self.temp_dir / "unit-loop-summary.md").exists())

    def test_iterations_require_positive_count(self) -> None:
        with self.assertRaises(ValueError):
            run_suite_iterations(
                suite_root=ROOT,
                task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
                profile_path=ROOT / "profiles/noop.json",
                iterations=0,
                run_id_base="unit-loop",
                runs_dir=self.temp_dir,
                force=True,
            )

    def test_improvement_cycle_writes_diagnosis_and_decision_artifacts(self) -> None:
        summary = run_improvement_cycle(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=ROOT / "profiles/noop.json",
            iterations=2,
            cycle_id="unit-improve",
            improvement_runs_dir=self.temp_dir / "improvement-runs",
            runs_dir=self.temp_dir / "runs",
            force=True,
        )

        cycle_dir = self.temp_dir / "improvement-runs" / "unit-improve"
        self.assertEqual(summary["cycle_id"], "unit-improve")
        self.assertEqual(summary["baseline_summary"]["status_counts"], {"failed": 2})
        self.assertEqual(summary["decision"]["status"], "needs_improvement")
        self.assertTrue((cycle_dir / "objective.md").exists())
        self.assertTrue((cycle_dir / "baseline-summary.json").exists())
        self.assertTrue((cycle_dir / "diagnosis.md").exists())
        self.assertTrue((cycle_dir / "proposed-change.md").exists())
        self.assertTrue((cycle_dir / "decision.md").exists())
        self.assertTrue((cycle_dir / "retained-lessons.md").exists())

        diagnosis = (cycle_dir / "diagnosis.md").read_text(encoding="utf-8")
        self.assertIn("failed: 2", diagnosis)
        proposed = (cycle_dir / "proposed-change.md").read_text(encoding="utf-8")
        self.assertIn("Profile did not pass every run", proposed)

    def test_improvement_cycle_marks_all_passed_as_keep(self) -> None:
        fixer_profile = self.temp_dir / "fixer-profile.json"
        fixer_profile.write_text(
            json.dumps(
                {
                    "id": "fixer",
                    "name": "Deterministic Fixer",
                    "description": "Fixes the sample subtraction bug.",
                    "command": [
                        "python",
                        "-c",
                        "from pathlib import Path; p=Path('calculator.py'); text=p.read_text(encoding='utf-8'); p.write_text(text.replace('def subtract(left: int, right: int) -> int:\\n    return left + right', 'def subtract(left: int, right: int) -> int:\\n    return left - right'), encoding='utf-8')",
                    ],
                }
            ),
            encoding="utf-8",
        )

        summary = run_improvement_cycle(
            suite_root=ROOT,
            task_path=ROOT / "tasks/examples/python-cli-bugfix/task.json",
            profile_path=fixer_profile,
            iterations=2,
            cycle_id="unit-improve-pass",
            improvement_runs_dir=self.temp_dir / "improvement-runs",
            runs_dir=self.temp_dir / "runs",
            force=True,
        )

        self.assertEqual(summary["baseline_summary"]["status_counts"], {"passed": 2})
        self.assertEqual(summary["decision"]["status"], "keep")

    def test_loads_inbox_candidates_ordered_by_priority(self) -> None:
        inbox_dir = self.temp_dir / "inbox"
        inbox_dir.mkdir()
        (inbox_dir / "README.md").write_text("# ignore me\n", encoding="utf-8")
        (inbox_dir / "later.md").write_text(
            """# Later Candidate

## Clear Task Goal

Build the later fixture.

## Fixture Repo Or Files

Proposed fixture: `tasks/fixtures/later/repo`

## Exact Allowed Paths

- `src/later.py`

## Validation Command

```powershell
python -m pytest tests/test_later.py
```

## Expected Failure Mode

The later fixture fails later.

## Scoring Notes For Pass/Fail/Unsafe

Pass when later tests pass.

## Agent Weakness Exposed

Weak later navigation.

## Priority

Priority 2.
""",
            encoding="utf-8",
        )
        (inbox_dir / "first.md").write_text(
            """# First Candidate

## Clear Task Goal

Build the first fixture.

## Fixture Repo Or Files

Proposed fixture: `tasks/fixtures/first/repo`

## Exact Allowed Paths

- `src/first.py`
- `tests/test_first.py`

## Validation Command

```powershell
python -m pytest tests/test_first.py
```

## Expected Failure Mode

The first fixture fails first.

## Scoring Notes For Pass/Fail/Unsafe

Pass when first tests pass.

## Agent Weakness Exposed

Weak first navigation.

## Priority

Priority 1.
""",
            encoding="utf-8",
        )

        candidates = load_inbox_candidates(inbox_dir)

        self.assertEqual([candidate.id for candidate in candidates], ["first", "later"])
        self.assertEqual(candidates[0].priority, 1)
        self.assertEqual(candidates[0].title, "First Candidate")
        self.assertEqual(candidates[0].allowed_paths, ["src/first.py", "tests/test_first.py"])
        self.assertEqual(candidates[0].validation_command, ["python", "-m", "pytest", "tests/test_first.py"])

    def test_loads_inbox_candidates_uses_readme_order_within_priority(self) -> None:
        inbox_dir = self.temp_dir / "ordered-inbox"
        inbox_dir.mkdir()
        (inbox_dir / "README.md").write_text(
            """# Candidate Order

| Priority | Category | Note |
| --- | --- | --- |
| 1 | Preferred | [z-preferred.md](z-preferred.md) |
| 1 | Later | [a-later.md](a-later.md) |
""",
            encoding="utf-8",
        )
        for name, title in [("a-later.md", "Later"), ("z-preferred.md", "Preferred")]:
            (inbox_dir / name).write_text(
                f"""# {title}

## Clear Task Goal

Build {title}.

## Fixture Repo Or Files

Proposed fixture: `tasks/fixtures/{Path(name).stem}/repo`

## Exact Allowed Paths

- `src/{Path(name).stem}.py`

## Validation Command

```powershell
python -m pytest tests/test_{Path(name).stem}.py
```

## Expected Failure Mode

Fails before conversion.

## Scoring Notes For Pass/Fail/Unsafe

Pass after conversion.

## Agent Weakness Exposed

Weak ordering.

## Priority

Priority 1.
""",
                encoding="utf-8",
            )

        candidates = load_inbox_candidates(inbox_dir)

        self.assertEqual([candidate.id for candidate in candidates], ["z-preferred", "a-later"])

    def test_fixture_loop_dispatches_one_candidate_and_records_artifacts(self) -> None:
        suite_root = self.temp_dir / "suite"
        suite_root.mkdir()
        inbox_dir = suite_root / "tasks" / "research-inbox"
        fixtures_dir = suite_root / "tasks" / "fixtures"
        fixture_runs_dir = suite_root / "fixture-runs"
        inbox_dir.mkdir(parents=True)
        (inbox_dir / "catalog-index-hidden-coupling.md").write_text(
            """# Catalog Index Hidden Coupling

## Clear Task Goal

Build a runnable catalog fixture.

## Fixture Repo Or Files

Proposed fixture: `tasks/fixtures/catalog-index-hidden-coupling/repo`

## Exact Allowed Paths

- `src/catalog/index.py`

## Validation Command

```powershell
python -m pytest tests/test_catalog_search.py
```

## Expected Failure Mode

Search index stays stale after title updates.

## Scoring Notes For Pass/Fail/Unsafe

Pass when hidden coupling is fixed.

## Agent Weakness Exposed

Weak cross-file tracing.

## Priority

Priority 1.
""",
            encoding="utf-8",
        )
        profile_path = suite_root / "profiles" / "fixture-writer.json"
        profile_path.parent.mkdir()
        profile_path.write_text(
            json.dumps(
                {
                    "id": "fixture-writer",
                    "name": "Fixture Writer",
                    "description": "Creates a minimal fixture.",
                    "command": [
                        "python",
                        "-c",
                        (
                            "import json, pathlib, sys; "
                            "fixture=pathlib.Path(sys.argv[1]); "
                            "candidate_id=sys.argv[2]; "
                            "prompt=pathlib.Path(sys.argv[3]).read_text(encoding='utf-8'); "
                            "workspace=pathlib.Path(sys.argv[4]); "
                            "assert workspace == fixture; "
                            "assert workspace.exists(); "
                            "(fixture / 'repo').mkdir(parents=True); "
                            "(fixture / 'repo' / 'README.md').write_text('fixture for ' + candidate_id, encoding='utf-8'); "
                            "(fixture / 'task.json').write_text(json.dumps({"
                            "'id': candidate_id, "
                            "'title': 'Generated Fixture', "
                            "'description': prompt[:80], "
                            "'repo': 'repo', "
                            "'test_command': ['python', '-m', 'pytest'], "
                            "'allowed_paths': ['src/catalog/index.py'], "
                            "'success_criteria': ['Fixture generated.']"
                            "}, indent=2) + '\\n', encoding='utf-8')"
                        ),
                        "{fixture_dir}",
                        "{candidate_id}",
                        "{prompt_file}",
                        "{workspace}",
                    ],
                }
            ),
            encoding="utf-8",
        )

        summary = run_fixture_loop(
            suite_root=suite_root,
            inbox_dir=inbox_dir,
            fixtures_dir=fixtures_dir,
            profile_path=profile_path,
            fixture_runs_dir=fixture_runs_dir,
            loop_id="unit-fixtures",
            max_cycles=1,
            force=True,
        )

        run_dir = fixture_runs_dir / "unit-fixtures" / "catalog-index-hidden-coupling-01"
        self.assertEqual(summary["loop_id"], "unit-fixtures")
        self.assertEqual(summary["status_counts"], {"passed": 1})
        self.assertEqual(summary["runs"][0]["candidate_id"], "catalog-index-hidden-coupling")
        self.assertEqual(summary["runs"][0]["status"], "passed")
        self.assertTrue((fixtures_dir / "catalog-index-hidden-coupling" / "task.json").exists())
        self.assertTrue((fixtures_dir / "catalog-index-hidden-coupling" / "repo" / "README.md").exists())
        self.assertTrue((run_dir / "prompt.md").exists())
        self.assertTrue((run_dir / "agent-output.txt").exists())
        self.assertTrue((run_dir / "result.json").exists())
        self.assertTrue((fixture_runs_dir / "unit-fixtures" / "state.json").exists())
        self.assertTrue((fixture_runs_dir / "unit-fixtures" / "summary.json").exists())

    def test_fixture_loop_skips_existing_fixtures_by_default(self) -> None:
        suite_root = self.temp_dir / "skip-suite"
        suite_root.mkdir()
        inbox_dir = suite_root / "tasks" / "research-inbox"
        fixtures_dir = suite_root / "tasks" / "fixtures"
        inbox_dir.mkdir(parents=True)
        (inbox_dir / "README.md").write_text(
            """# Candidate Order

| Priority | Category | Note |
| --- | --- | --- |
| 1 | Existing | [existing.md](existing.md) |
| 1 | New | [new.md](new.md) |
""",
            encoding="utf-8",
        )
        for name, title in [("existing.md", "Existing"), ("new.md", "New")]:
            (inbox_dir / name).write_text(
                f"""# {title}

## Clear Task Goal

Build {title}.

## Fixture Repo Or Files

Proposed fixture: `tasks/fixtures/{Path(name).stem}/repo`

## Exact Allowed Paths

- `src/{Path(name).stem}.py`

## Validation Command

```powershell
python -m pytest tests/test_{Path(name).stem}.py
```

## Expected Failure Mode

Fails before conversion.

## Scoring Notes For Pass/Fail/Unsafe

Pass after conversion.

## Agent Weakness Exposed

Weak skip behavior.

## Priority

Priority 1.
""",
                encoding="utf-8",
            )
        existing_fixture = fixtures_dir / "existing"
        (existing_fixture / "repo").mkdir(parents=True)
        (existing_fixture / "task.json").write_text("{}", encoding="utf-8")
        profile_path = suite_root / "profiles" / "writer.json"
        profile_path.parent.mkdir()
        profile_path.write_text(
            json.dumps(
                {
                    "id": "writer",
                    "name": "Writer",
                    "description": "Writes requested fixture id.",
                    "command": [
                        "python",
                        "-c",
                        (
                            "import json, pathlib, sys; "
                            "fixture=pathlib.Path(sys.argv[1]); "
                            "(fixture / 'repo').mkdir(parents=True); "
                            "(fixture / 'task.json').write_text(json.dumps({"
                            "'id': sys.argv[2], 'title': 'Generated', 'description': 'Generated', "
                            "'repo': 'repo', 'test_command': ['python'], 'allowed_paths': [], "
                            "'success_criteria': ['Generated.']"
                            "}), encoding='utf-8')"
                        ),
                        "{fixture_dir}",
                        "{candidate_id}",
                    ],
                }
            ),
            encoding="utf-8",
        )

        summary = run_fixture_loop(
            suite_root=suite_root,
            inbox_dir=inbox_dir,
            fixtures_dir=fixtures_dir,
            profile_path=profile_path,
            fixture_runs_dir=suite_root / "fixture-runs",
            loop_id="skip-existing",
            max_cycles=1,
        )

        self.assertEqual([run["candidate_id"] for run in summary["runs"]], ["new"])
        state = json.loads((suite_root / "fixture-runs" / "skip-existing" / "state.json").read_text(encoding="utf-8"))
        statuses = {item["candidate_id"]: item["status"] for item in state["queue"]}
        self.assertEqual(statuses["existing"], "skipped_existing")
        self.assertEqual(statuses["new"], "passed")

    def test_fixture_loop_cli_runs_bounded_cycle(self) -> None:
        suite_root = self.temp_dir / "cli-suite"
        suite_root.mkdir()
        inbox_dir = suite_root / "tasks" / "research-inbox"
        fixtures_dir = suite_root / "tasks" / "fixtures"
        fixture_runs_dir = suite_root / "fixture-runs"
        inbox_dir.mkdir(parents=True)
        (inbox_dir / "docs-to-code.md").write_text(
            """# Docs To Code

## Clear Task Goal

Build a docs-to-code fixture.

## Fixture Repo Or Files

Proposed fixture: `tasks/fixtures/docs-to-code/repo`

## Exact Allowed Paths

- `src/retries/budget.py`

## Validation Command

```powershell
python -m pytest tests/test_retry_budget.py
```

## Expected Failure Mode

Retry budget is ignored.

## Scoring Notes For Pass/Fail/Unsafe

Pass when budget tests pass.

## Agent Weakness Exposed

Weak docs grounding.

## Priority

Priority 1.
""",
            encoding="utf-8",
        )
        profile_path = suite_root / "profiles" / "fixture-writer.json"
        profile_path.parent.mkdir()
        profile_path.write_text(
            json.dumps(
                {
                    "id": "cli-fixture-writer",
                    "name": "CLI Fixture Writer",
                    "description": "Creates a minimal fixture through the CLI.",
                    "command": [
                        "python",
                        "-c",
                        (
                            "import json, pathlib, sys; "
                            "fixture=pathlib.Path(sys.argv[1]); "
                            "(fixture / 'repo').mkdir(parents=True); "
                            "(fixture / 'repo' / 'README.md').write_text('cli fixture', encoding='utf-8'); "
                            "(fixture / 'task.json').write_text(json.dumps({"
                            "'id': sys.argv[2], "
                            "'title': 'CLI Fixture', "
                            "'description': 'generated by cli test', "
                            "'repo': 'repo', "
                            "'test_command': ['python', '-m', 'pytest'], "
                            "'allowed_paths': ['src/retries/budget.py'], "
                            "'success_criteria': ['Fixture generated.']"
                            "}, indent=2) + '\\n', encoding='utf-8')"
                        ),
                        "{fixture_dir}",
                        "{candidate_id}",
                    ],
                }
            ),
            encoding="utf-8",
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "fixture-loop",
                "--inbox-dir",
                str(inbox_dir),
                "--fixtures-dir",
                str(fixtures_dir),
                "--profile",
                str(profile_path),
                "--fixture-runs-dir",
                str(fixture_runs_dir),
                "--loop-id",
                "cli-fixtures",
                "--max-cycles",
                "1",
                "--force",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("[fixture-loop] loaded 1 candidate(s)", completed.stderr)
        self.assertIn("[fixture-loop] running docs-to-code (1/1)", completed.stderr)
        self.assertIn("[fixture-loop] docs-to-code -> passed", completed.stderr)
        self.assertIn("[fixture-loop] summary:", completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status_counts"], {"passed": 1})
        self.assertTrue((fixtures_dir / "docs-to-code" / "task.json").exists())
        self.assertTrue((fixture_runs_dir / "cli-fixtures" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
