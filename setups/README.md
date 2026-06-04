# Setups — the kit you give your AI

A **setup** is a named folder holding everything you hand your AI coding assistant
*before* you point it at a challenge: an instruction file, some skills, and an
optional context-pack. It's the thing being measured — change your setup, change
your score.

The suite ships a few generic examples so you can see what one looks like. Copy one,
or make your own.

## What's in a setup

```
setups/<your-setup>/
  setup.json     # manifest: name, the agent/model it's for, which files it uses
  CLAUDE.md      # the instructions your AI loads (any name; set in setup.json)
  skills/
    <skill>/SKILL.md   # one folder per skill — a reusable habit for your agent
```

`setup.json` fields (see `schemas/setup.schema.json`):

| field | meaning |
|-------|---------|
| `id`, `name` | required; identity + display name |
| `description` | one line shown on the setup card |
| `agent`, `model` | what tool/model this kit is for (free text) |
| `instructions_file` | the instruction file in this folder, or `null` |
| `skills` | list of skill folder names under `skills/` |
| `context_pack` | an id from `context-packs/`, or `null` |

## Make a new one

```
python run.py setup new my-kit      # scaffolds setups/my-kit/
# edit setups/my-kit/CLAUDE.md and add skills/, then:
python run.py setup validate my-kit # checks the manifest + files (and warns on task-specific hints)
python generate_setups_data.py      # refresh what the GUI shows
```

## See them

- `python run.py setup list` — all setups at a glance
- `python run.py setup show my-kit` — print a setup's files
- Open `index.html` — the **Setups** section renders every setup, read-only.

## The one rule

A setup must be **general**. It may NOT contain answers or hints for specific
challenges — that defeats the benchmark. `setup validate` warns if a setup's text
mentions a challenge id. A good setup teaches good habits (verify, stay in scope),
not solutions.

## Sharing a score

When you record a result, tag it with the setup you used so the leaderboard can
link the score back to the kit that earned it:

```
python run.py score-set tasks/eval-sets/core.json --setup my-kit \
  --agent "My Kit (Claude)" --model claude-opus-4-8 --emit-entry my-kit-core
```
