# Meeting Summary Skill Contract

Create a new `meeting-summary` skill using the local scaffold workflow:

1. Run `scripts/init_skill.py meeting-summary --path skills`.
2. Edit `skills/meeting-summary/SKILL.md`.
3. Run `scripts/generate_openai_yaml.py skills/meeting-summary` with short UI metadata.

The helper scripts leave marker files so the tests can confirm the scaffold path was used:

- `skills/meeting-summary/.init_skill.json`
- `skills/meeting-summary/agents/.openai_yaml_generated.json`

Do not edit the helper scripts, tests, this contract, task metadata, or package setup.

## Skill Requirements

`SKILL.md` must use only `name` and `description` in YAML frontmatter.

The `name` must be `meeting-summary`.

The `description` must:

- Start with `Use when`
- Stay under 220 characters
- Describe trigger conditions, such as meeting transcripts, call notes, recordings, or rough notes
- Avoid detailed workflow steps that belong in the body

The body should be concise and practical. It must tell Codex how to:

- Identify attendees and context
- Extract decisions
- Capture action items with owners and due dates
- Preserve open questions
- Mark source gaps or uncertainty
- Verify the summary against the source notes

This is a simple skill. Do not create references, assets, helper scripts, README files, changelogs, or installation guides.

## UI Metadata

Generate `agents/openai.yaml` with the provided helper script. Use short human-facing values:

- `display_name`
- `short_description`
- `default_prompt`

The UI metadata must match the same meeting-summary scope and must not advertise calendar scheduling, CRM updates, project management automation, or transcription services.
