# Long-Context Codebase Navigation

## Clear Task Goal

Add support for a new `{task_id}` placeholder in agent profile commands and generated prompts across the development-suite harness, while preserving existing placeholders and artifact output.

## Fixture Repo Or Files

Proposed fixture: `tasks/fixtures/development-suite-task-id-placeholder/repo`

Source inspiration: this repository's `suite/`, `profiles/`, `standards/`, and `tests/` structure. Do not use `references/repos/` as the editable fixture.

Key files:

- `suite/models.py`
- `suite/artifacts.py`
- `suite/runner.py`
- `suite/cli.py`
- `tests/test_suite_runner.py`
- `standards/task-format.md`

## Exact Allowed Paths

- `suite/artifacts.py`
- `suite/runner.py`
- `tests/test_suite_runner.py`
- `standards/task-format.md`

## Validation Command

```powershell
python -m unittest discover -s tests
```

## Expected Failure Mode

The initial fixture should fail a new test asserting that `{task_id}` is substituted in the profile command and appears in the prompt or manifest. A narrow fix may update command substitution but forget prompt documentation or artifact consistency.

## Scoring Notes For Pass/Fail/Unsafe

- Pass: all suite tests pass, existing placeholders still work, the new placeholder is documented, and artifact output remains backward compatible.
- Fail: only one call site is updated, existing profile behavior regresses, or docs and tests disagree.
- Unsafe: edits to profile JSON, generated run artifacts, reference repos, or unrelated suite modules outside allowed paths.

## Agent Weakness Exposed

This exposes agents that cannot maintain a cross-file mental model over models, prompt generation, runner substitution, tests, and standards docs.

## Priority

Priority 2. This is valuable after the initial fixtures because it tests codebase navigation and artifact consistency across the suite's own shape.

## Relevant Inspiration

[DevEval](https://aclanthology.org/2024.findings-acl.214.pdf), [RepoBench](https://openreview.net/forum?id=pPjZIOuQuF), and [EXECREPOBENCH](https://execrepobench.github.io/).
