# Local Skill Contract

This contract defines the skill quality bar for this fixture.

## Required Shape

- The only editable file is `skills/incident-triage/SKILL.md`.
- The file must start with YAML frontmatter delimited by `---`.
- Frontmatter must include `name` and `description`.
- `name` must be lowercase hyphen-case and match the folder: `incident-triage`.
- `description` must start with `Use when`.
- The description should be trigger-only. It should describe when the skill applies, not summarize workflow steps.

## Body Requirements

The body must be reusable procedure documentation, not a story about a single incident.

It must include:

- A short overview.
- A "When to Use" section.
- A triage workflow that covers intake, reproduction, severity, evidence capture, mitigation, and handoff.
- A "Verification" section with concrete completion checks.
- A "Common Mistakes" section that warns against guessing, silent mitigation, and skipping evidence.

## Style Requirements

- Keep the skill concise.
- Use concrete commands or artifacts where useful.
- Avoid vague phrases such as "handle appropriately", "do the needful", and "etc.".
- Do not add extra documentation files for this exercise.
