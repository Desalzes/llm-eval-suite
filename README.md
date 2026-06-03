# LLM Testing Suite

This repository is a standalone test corpus extracted from `C:\Users\desal\ChatGPT`.
It is intended to become the source of truth for LLM evaluation fixtures and, later,
the backing data for a GUI.

## Contents

- `index.html` - Static visual atlas GUI for browsing the current test corpus.
- `generate_atlas_data.py` - Regenerates `atlas-data.js` from the real corpus.
- `atlas-data.js` - Auto-generated data the atlas renders (do not edit by hand).
- `tasks/` - LLM-facing task fixtures, examples, eval sets, relay handoff fixtures,
  and research-inbox candidates.
- `tests/` - Python tests from the original harness repo.
- `schemas/` - JSON Schema contracts used by task, profile, eval, handoff, and result files.
- `standards/` - Human-readable scoring and task-format standards.
- `profiles/` - Agent profile JSON files copied for reference.
- `context-packs/` - Prompt/context packs used by supervised and verification flows.

Generated runtime artifacts such as caches, run outputs, virtual environments, and
node dependencies are intentionally excluded.

## Open The Visual Atlas

Open `index.html` in a browser. The page is static and does not need a dev server.

The metric strip, fixture cards, category/risk charts, and reference counts are
rendered from `atlas-data.js`, which is **generated from the real corpus** rather
than hand-maintained. After adding or editing fixtures, eval sets, schemas, or
profiles, regenerate it:

    python generate_atlas_data.py

`tests/test_generate_atlas_data.py` checks the generated data stays consistent with
the corpus on disk, and `tests/test_visual_atlas_static.py` checks the page is wired
to load that data. Run both with:

    python -m pytest tests/test_generate_atlas_data.py tests/test_visual_atlas_static.py
