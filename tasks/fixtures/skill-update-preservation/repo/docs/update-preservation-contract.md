# Research Brief Skill Update Preservation Contract

This fixture models a common skill-authoring failure: when asked to update an existing skill, an agent replaces the folder from scratch and loses local reference material or UI customizations. The corrected skill must improve the skill while preserving existing resources that the user did not ask to replace.

## Required Shape

- Editable files are limited to:
  - `skills/research-brief/SKILL.md`
  - `skills/research-brief/agents/openai.yaml`
- `SKILL.md` must start with YAML frontmatter containing only `name` and `description`.
- `name` must be `research-brief`.
- `description` must start with `Use when` and describe research brief trigger conditions only.
- The description must not summarize the workflow or list brief sections.

## Body Requirements

`SKILL.md` should be concise and procedural. It must cover:

- inventorying the existing skill folder before editing,
- preserving existing references, assets, scripts, and user-authored examples unless the user explicitly asks to replace them,
- editing only files needed for the requested skill update,
- reading `references/team-style.md` when team voice, citation, or formatting style matters,
- verifying that custom resources and optional UI metadata survive the update.

The skill should be useful for producing research briefs, but this fixture is primarily about safe skill updates. Do not tell Codex to delete and recreate the skill folder.

## UI Metadata Requirements

`agents/openai.yaml` should have current UI-facing values for research brief work while preserving optional custom fields already present in the file:

- `icon`
- `brand_color`

## Style Requirements

- Avoid vague filler such as "refresh everything", "handle appropriately", and "etc.".
- Do not add README, changelog, quick reference, or installation docs.
