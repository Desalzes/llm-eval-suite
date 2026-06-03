# Research Inbox Task Candidates

These notes are pre-suite task candidates. They are intentionally richer than the current `task.json` schema so they can be reviewed before being converted into runnable fixtures.

Current suite mapping:

- `Task goal` maps into `title` and `description`.
- `Fixture repo/files` maps into `repo` after the fixture is created.
- `Exact allowed paths` maps into `allowed_paths`.
- `Validation command` maps into `test_command`.
- `Scoring notes` should become success criteria plus any future rubric extensions.

## Candidates

| Priority | Category | Note |
| --- | --- | --- |
| 1 | Multi-file bugfix with hidden coupling | [multi-file-hidden-coupling.md](multi-file-hidden-coupling.md) |
| 1 | Docs-to-code implementation | [docs-to-code-implementation.md](docs-to-code-implementation.md) |
| 1 | Dependency/API migration | [dependency-api-migration.md](dependency-api-migration.md) |
| 2 | Flaky test diagnosis | [flaky-test-diagnosis.md](flaky-test-diagnosis.md) |
| 2 | Ambiguous product request with acceptance criteria | [ambiguous-product-request.md](ambiguous-product-request.md) |
| 2 | Long-context codebase navigation | [long-context-navigation.md](long-context-navigation.md) |
| 3 | "Do not touch" safety boundary task | [do-not-touch-safety-boundary.md](do-not-touch-safety-boundary.md) |
| 3 | Refactor with strict behavior preservation | [refactor-behavior-preservation.md](refactor-behavior-preservation.md) |
| 4 | Frontend visual regression, deferred/high-compute | [frontend-visual-regression.md](frontend-visual-regression.md) |

## Conversion Notes

- Keep reference repositories under `references/repos/` read-only. If a task borrows an idea from a reference repo, copy the minimum fixture into `tasks/fixtures/<task-id>/repo`.
- Prefer fixtures that fail before agent work and pass after a focused change.
- Keep allowed paths narrow enough that the suite can classify boundary violations as `unsafe`.
- Store any visual baselines, golden files, or docs inside the fixture repo so the runner copy is self-contained.
- Start with priority 1 candidates and make them runnable before expanding the suite width.
- Keep visual/browser fixtures out of the default loop unless explicitly requested.
