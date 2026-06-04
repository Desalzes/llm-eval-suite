# Setup format

A *setup* is the kit you give your AI before a run: instructions + skills (+ an
optional context-pack). It is what the score measures. Setups live under
`setups/<id>/`; the GUI's **Setups** section renders them read-only.

## Folder

    setups/<id>/
      setup.json          # manifest (required)
      <instructions_file> # e.g. CLAUDE.md or AGENTS.md (optional)
      skills/
        <skill>/SKILL.md  # one folder per skill (optional)

## `setup.json`

Validated by `schemas/setup.schema.json` and `run.py setup validate`.

| field | required | meaning |
|-------|----------|---------|
| `id` | yes | stable identifier; matches the folder name |
| `name` | yes | display name on the setup card |
| `description` | no | one line shown on the card |
| `agent` | no | the tool this kit targets (free text, e.g. "Claude Code") |
| `model` | no | model id or `null` |
| `instructions_file` | no | the instruction file in this folder, or `null` |
| `skills` | no | list of skill folder names under `skills/` |
| `context_pack` | no | an id from `context-packs/`, or `null` |
| `badges` | no | display tags, e.g. `["example"]`, `["baseline"]` |
| `created` | no | ISO date |

## Validity rules

1. `setup.json` parses and has `id` + `name`.
2. `instructions_file`, if set, exists in the folder.
3. Every entry in `skills` has a `skills/<name>/SKILL.md`.
4. **General, not task-specific.** A setup must not contain answers or hints for
   any specific challenge. `run.py setup validate` warns if a setup's text mentions
   a challenge id. Task-specific setups defeat the benchmark.

## Linking a setup to a score

`run.py score-set ... --setup <id>` stamps `setup_id` on the eval-summary /
leaderboard entry, so the board links each score back to the kit that earned it.
The suite never copies a setup into a task workspace (that would score `unsafe`,
and some challenges legitimately grade `.claude/`/`SKILL.md` content); you
configure your own agent with the setup, and the suite records which one you used.
