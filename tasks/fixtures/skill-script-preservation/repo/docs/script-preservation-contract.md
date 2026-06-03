# Script Preservation Skill Contract

This fixture checks whether a skill author keeps deterministic helper logic in a script instead of turning it into fragile prose.

## Required Files

Editable files are limited to:

- `skills/csv-normalization/SKILL.md`
- `skills/csv-normalization/scripts/normalize_csv.py`

Do not add README files, changelogs, quick references, or installation guides.

## SKILL.md Requirements

- Frontmatter must contain only `name` and `description`.
- `name` must be `csv-normalization`.
- The description must start with `Use when` and describe trigger conditions only.
- The body must stay concise and procedural.
- The body must point to `scripts/normalize_csv.py` for deterministic CSV cleanup.
- The body must avoid embedding a full CSV parser or script listing.

## Script Requirements

`scripts/normalize_csv.py` should be a standard-library CLI:

```text
python skills/csv-normalization/scripts/normalize_csv.py --input messy.csv --output clean.csv
```

The script must:

- read UTF-8 CSV input,
- normalize headers by trimming whitespace, lowercasing, replacing non-alphanumeric runs with `_`, and trimming leading/trailing `_`,
- trim whitespace around every cell,
- drop fully blank rows,
- preserve row order and non-whitespace cell values,
- write UTF-8 CSV output with normalized headers.

Do not use pandas or network calls for this fixture.

## Style Requirements

- Keep `SKILL.md` under 420 words.
- Avoid vague filler such as "handle appropriately", "just clean it up", and "etc.".
- Prefer telling Codex when to run or inspect the script over restating the whole implementation in prose.
