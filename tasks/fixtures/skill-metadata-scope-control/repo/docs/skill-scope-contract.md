# Data Export Skill Scope Contract

This fixture models a common skill-authoring mistake: one skill tries to cover every adjacent analytics task. The corrected skill must stay narrow enough to trigger reliably and keep detailed checks outside the main SKILL.md body.

## Required Shape

- Editable files are limited to:
  - `skills/data-export/SKILL.md`
  - `skills/data-export/agents/openai.yaml`
  - `skills/data-export/references/export-checklist.md`
- `SKILL.md` must start with YAML frontmatter containing only `name` and `description`.
- `name` must be `data-export`.
- `description` must start with `Use when` and describe data export trigger conditions only.
- The description must not advertise dashboards, BI, data warehouse migrations, notebooks, modeling, or general analytics.

## Body Requirements

`SKILL.md` should be concise and procedural. It must cover:

- confirming requested output format and destination,
- checking schema, filters, row counts, and privacy constraints,
- generating or validating the export,
- reading `references/export-checklist.md` only when detailed export validation is needed,
- verification before finishing.

Detailed CSV, Parquet, schema, privacy, and delivery checks belong in `references/export-checklist.md`, not in the main skill body.

## UI Metadata

`agents/openai.yaml` should match the narrowed skill. Use short human-facing values:

- `display_name`
- `short_description`
- `default_prompt`

The metadata should not mention unrelated analytics areas.

## Style Requirements

- Avoid vague filler such as "handle data appropriately", "do the export correctly", and "etc.".
- Do not add README, changelog, quick reference, or installation docs.
