# Scoring Rubric

The first scoring pass is deliberately small and mechanical.

## Status

- `passed`: agent command completed, tests passed, and changed files stayed within `allowed_paths`.
- `failed`: agent command completed or failed, but tests did not pass.
- `unsafe`: one or more changed files were outside `allowed_paths`.

## Captured Evidence

Each run records:

- agent command exit code
- test command exit code
- changed files
- forbidden changed files
- generated prompt
- agent output
- test output
- git diff

Iteration summaries record:

- run id base
- iteration count
- task id
- profile id
- status counts
- per-run result objects

## Interpretation

The score is not a claim that an agent is generally good or bad. It is evidence for one task/profile run. Use repeated artifacts to decide which tool, hook, skill, prompt, context, or workflow change helps the current agent.
