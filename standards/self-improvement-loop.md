# Self-Improvement Loop

The suite improves agent workflow, not model weights.

## Loop

1. Choose a task, profile, and context pack.
2. Run bounded iterations.
3. Collect artifacts: prompts, outputs, diffs, tests, and summaries.
4. Diagnose observed failures without guessing about model internals.
5. Propose a tool, hook, skill, prompt, context, profile, or standard change.
6. Rerun the same task/profile/context combination.
7. Keep changes only when evidence improves.
8. Retain lessons as auditable artifacts.

## What Improvement Means

Improvement can mean:

- higher pass rate
- lower unsafe-change rate
- smaller required context
- fewer changed files
- clearer final artifacts
- less repeated failure on the same task class

## Guardrail

An improvement cycle is evidence for one task/profile/context combination. It is not a general claim about a model and is not meant to rank multiple LLMs.
