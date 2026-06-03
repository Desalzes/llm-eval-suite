# Task Format

Development-suite tasks are JSON files that describe one bounded coding assignment.

Required fields:

- `id`: stable machine-readable task id.
- `title`: short human-readable task title.
- `description`: task brief sent to the agent.
- `repo`: path to the fixture or target repository, relative to the task file unless absolute.
- `test_command`: command array run after the agent completes.
- `allowed_paths`: file globs the agent is allowed to modify.
- `success_criteria`: checklist items included in the generated prompt and review artifact.

Example:

```json
{
  "id": "python-cli-bugfix",
  "title": "Fix calculator subtraction",
  "description": "Fix the calculator so subtraction returns the expected value.",
  "repo": "repo",
  "test_command": ["python", "-m", "unittest", "discover"],
  "allowed_paths": ["calculator.py"],
  "success_criteria": [
    "All tests pass.",
    "Only calculator.py is modified."
  ]
}
```

The first harness milestone copies the task repo into `runs/<run-id>/workspace` before running an agent profile. Source fixtures stay unchanged.
