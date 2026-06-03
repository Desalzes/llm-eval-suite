# CRM Sync Skill Prerequisite Boundary Contract

This fixture models a common skill-authoring mistake: an integration skill assumes credentials, connector access, and permission to write records. The corrected skill must be useful without pretending those prerequisites already exist.

## Required Shape

- Editable files are limited to `skills/crm-sync/SKILL.md`.
- `SKILL.md` must start with YAML frontmatter containing only `name` and `description`.
- `name` must be `crm-sync`.
- `description` must start with `Use when` and describe CRM sync trigger conditions only.
- The description must not summarize the workflow or claim that the skill logs into systems, creates credentials, writes records, or performs deduplication automatically.

## Body Requirements

`SKILL.md` should be concise and procedural. It must cover:

- required prerequisites before any sync work:
  - source system,
  - destination system,
  - connected app or credentials,
  - workspace or tenant context,
  - record types and field scope;
- read-only discovery before writes:
  - inspect available records,
  - map fields,
  - produce a dry-run or preview,
  - get explicit confirmation before updating records;
- missing-access fallback:
  - ask for connector access, exported files, or sample rows,
  - state that Codex must not invent records, credentials, or hidden permissions,
  - provide a manual checklist or plan if live access is unavailable;
- verification:
  - record counts,
  - sample spot checks,
  - skipped conflicts,
  - rollback or backup plan.

## Style Requirements

- Avoid vague filler such as "handle appropriately", "do the needful", and "etc.".
- Do not tell Codex to paste, store, hard-code, or create API keys, passwords, tokens, or secrets.
- Do not add README, changelog, quick reference, or installation docs.
