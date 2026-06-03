# Trigger Boundary Contract

Revise `skills/release-notes/SKILL.md` so it is a narrow, useful skill for drafting
release notes from supplied source material.

The frontmatter is the trigger surface. It should use:

- `name: release-notes`
- a `description` that starts with `Use when`
- concise wording that triggers for release notes, changelog-to-release-note conversion,
  or summarizing shipped product changes for users

The frontmatter must not make the skill look useful for every adjacent product-writing
task. Avoid trigger terms for pull request review, commit-message writing, marketing copy,
general documentation, ticket triage, and "all product work".

The body should stay short and include:

- what inputs to collect: audience, release period or version, source list, tone, and
  shipped changes
- when not to use the skill
- a workflow that groups user-facing changes separately from internal chores, refactors,
  and bugfixes
- a rule to ask for missing inputs instead of inventing changes, dates, audiences, or
  source links
- verification checks for source grounding, audience fit, uncertainty, and omitted
  internal-only work

Do not create extra README, changelog, quick-reference, or installation-guide files.
