# Contributing a challenge

Anyone can add a challenge. A challenge is valid if it **abides by the template** — and
there's a one-command check (`python run.py validate`) that tells you whether it does.

## What a challenge is

A self-contained coding problem in its own folder:

    tasks/community/<your-id>/
      task.json        # the brief + the rules (fields below)
      repo/            # the code under test
        ...            # source files
        test_*.py      # grader tests that FAIL now and PASS once the task is solved

Copy [`tasks/template/`](tasks/template/) to `tasks/community/<your-id>/` and fill it in.

## `task.json` fields (all required)

| Field | Meaning |
|---|---|
| `id` | unique, lowercase-with-dashes (match your folder name) |
| `title` | short human title |
| `description` | the brief sent to the AI — **state the goal, not how to do it** (no hints) |
| `repo` | path to the code folder, relative to `task.json` (usually `"repo"`) |
| `test_command` | the grading command as a list, e.g. `["python","-m","unittest","discover"]` |
| `allowed_paths` | the only files the AI may change, as globs (keep this tight) |
| `success_criteria` | plain-English checklist shown to the AI |

Contract: [`schemas/task.schema.json`](schemas/task.schema.json). Notes: [`standards/task-format.md`](standards/task-format.md).

## The rules a valid challenge must follow

1. **Self-contained** — no network; minimal, standard dependencies (prefer Python stdlib + `unittest`). Declare anything extra.
2. **Fails before, passes after** — the grader tests must FAIL on the shipped code and PASS once the intended change is made. (`validate` checks this.)
3. **Tight `allowed_paths`** — list only what a correct solution must touch, so "unsafe" means something.
4. **Deterministic** — same code, same result every time.
5. **Bounded** — a focused problem, not a whole app.
6. **Don't ship the solution** — no answer files, no hints, no `skills/` that solve it.

## Author it with your AI (optional)

> Read `CONTRIBUTING.md` and `tasks/template/`. Create a new challenge under
> `tasks/community/<id>/` that tests <the skill you want to probe>. Make the grader tests
> fail on the starting code and pass once it's fixed. Then run
> `python run.py validate tasks/community/<id>/task.json` and fix anything it reports.

## Check it abides by the template

    python run.py validate tasks/community/<your-id>/task.json

Prints `VALID` (exit 0) when it conforms, or `INVALID` with reasons. Fix until valid.

## Submit

1. Regenerate the atlas: `python generate_atlas_data.py`
2. Run the tests: `python -m pytest tests/`
3. Open a pull request.

A maintainer reviews community submissions and **promotes** strong ones into
`tasks/fixtures/` and the scored eval-sets.
