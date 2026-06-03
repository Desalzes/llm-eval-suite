# Relay Handoff: ROOT

scope_marker: `MASTER:`
project: `ChatGPT root suite`

## Hard Rules

- Start root master user-visible responses with MASTER:.
- Keep .claude read-only unless explicitly scoped.
- Treat references/repos/ as read-only external context unless explicitly asked to work inside a reference repo.

## Source Boundaries

- Root suite source is C:/Users/desal/ChatGPT.
- First-party relay fixture files live under tasks/relay-handoff-fixtures/.
- Project-pack authority reads are not required for this ROOT fixture.

## Changed Files

- The root relay fixture and dynamic fixture tests changed, but this summary omits the exact file list.

## Generated Artifacts

- runs/relay-handoff/root-basic/formats/handoff.json
- runs/relay-handoff/root-basic/formats/handoff.md
- runs/relay-handoff/root-basic/scores.json

## Unresolved Risks

- Relay scoring remains deterministic local scoring only; no model-call preservation benchmark exists yet.
- ROOT-scoped handoffs may not include project-pack authority reads.

## Next Action

Use dynamic fixture coverage to keep every relay handoff fixture schema-valid and scoreable across supported formats.

## Verification Evidence

- Focused relay fixture tests were run, but this summary omits exact commands and evidence values.

## Project Pack Authority Reads

- none
