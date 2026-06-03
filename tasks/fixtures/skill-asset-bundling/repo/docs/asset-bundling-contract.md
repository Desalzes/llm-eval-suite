# Proposal Pack Skill Asset Contract

This fixture models a common skill-authoring mistake: a reusable output template is pasted into `SKILL.md`, making the skill noisy and harder to maintain. The corrected skill must keep procedural guidance in `SKILL.md` and move the reusable proposal template into `assets/proposal-template.md`.

## Required Shape

- Editable files are limited to:
  - `skills/proposal-pack/SKILL.md`
  - `skills/proposal-pack/assets/proposal-template.md`
- `SKILL.md` must start with YAML frontmatter containing only `name` and `description`.
- `name` must be `proposal-pack`.
- `description` must start with `Use when` and describe proposal-pack trigger conditions only.
- The description must not summarize the workflow or list proposal sections.

## Body Requirements

`SKILL.md` should be concise and procedural. It must cover:

- confirming audience, offer, decision stage, deadline, and required format,
- reading `assets/proposal-template.md` when a reusable proposal draft is needed,
- adapting the template to the user's context instead of copying placeholders blindly,
- verifying scope, assumptions, timeline, pricing inputs, and approval language before finishing.

The full reusable proposal template belongs in `assets/proposal-template.md`, not in the main skill body.

## Asset Requirements

`assets/proposal-template.md` must be directly usable as a proposal starting point. It should contain clear placeholders and sections for:

- client name,
- project summary,
- objectives,
- scope,
- out of scope,
- timeline,
- assumptions,
- pricing,
- approval.

## Style Requirements

- Avoid vague filler such as "customize as needed", "handle appropriately", and "etc.".
- Do not add README, changelog, quick reference, or installation docs.
