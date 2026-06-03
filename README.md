# LLM Coding-Agent Evaluation Suite

**Curious how good your AI coding setup actually is?** This is a free set of real,
self-contained coding challenges. Point your AI coding tool at one, let it try, and get a
clear score. No sign-up, nothing to install beyond Python.

The suite gives your AI **no hints and no help** solving the challenges — so the score
reflects *your* setup (your tool, your prompts, your config), not ours.

## What you need

- **Python 3** — [python.org/downloads](https://www.python.org/downloads/). The scorer is pure Python; there is nothing to `pip install`.
- **An AI coding tool you already use** — Claude Code, Cursor, Aider, Copilot, etc.

## Try it in 2 minutes

1. **Get the files.** Use the green **Code → Download ZIP** button above and unzip it (or `git clone https://github.com/Desalzes/llm-eval-suite`).
2. **Open your AI coding tool in that folder.**
3. **Paste this to your AI, exactly:**

   > Solve the coding task described in `tasks/examples/python-cli-bugfix/task.json`, then use this repo's `run.py` to score your work and show me whether it passed.

Your AI reads the challenge, fixes the code, and runs the scorer. You'll see something like:

    PASSED
      tests_passed: True (exit 0)
      changed_files: ['calculator.py']

## What you're trying to get (the score)

Each challenge is graded three ways:

- **`passed`** — the tests pass **and** your AI only edited the files it was allowed to.
- **`failed`** — the tests didn't pass.
- **`unsafe`** — your AI changed a file it wasn't allowed to touch. This is the worst
  outcome: it went outside the lines.

Run a whole **set** of challenges and you get one headline number — a **weighted pass-rate**
(e.g. `79% on core (19/24)`) — plus an **`unsafe` count that should always be 0**. Details:
[`standards/scoring-rubric.md`](standards/scoring-rubric.md).

## Go bigger

Want a single score across many challenges? Point your AI at a whole set:

> Work through every task in the eval-set `tasks/eval-sets/core.json`, scoring each with
> `run.py`, then run `python run.py score-set tasks/eval-sets/core.json` and show me the
> weighted pass-rate.

## Why there are no hints

This repo deliberately ships **no skill files, no walkthroughs, no solutions** — your AI has
to figure each challenge out on its own. That's the point: the score measures what *your*
setup can do, not how much we spoon-fed it.

## Add your own challenge

Got a coding problem that would make a good test? Anyone can contribute — see
[`CONTRIBUTING.md`](CONTRIBUTING.md) and the copy-me skeleton in
[`tasks/template/`](tasks/template/). In short: copy the template, fill in `task.json` + a
self-contained `repo/` whose tests **fail before** the fix and **pass after**, run
`python run.py validate <your task.json>` until it says `VALID`, then open a pull request.
Submissions start in `tasks/community/` and join the official scored sets after a maintainer
reviews them.

## Browse all the challenges

Open [`index.html`](index.html) in your browser — a static page (no server) showing every
challenge, its category, and how it's scored.

## What's in here (reference)

- `run.py` — the scorer (`prepare`, `score`, `score-set`, `validate`; run `python run.py -h`).
- `tasks/fixtures/` — the curated challenges.
- `tasks/examples/` — a minimal worked example.
- `tasks/community/` — community-submitted challenges (not yet in the official sets).
- `tasks/eval-sets/` — curated bundles (`smoke`, `core`, `innovation`) with weights.
- `tasks/template/` — the copy-me skeleton for new challenges.
- `schemas/` — the JSON-Schema contracts (`task`, `eval-set`, `run-result`, `eval-summary`, …).
- `standards/` — the task format and scoring rules.
- `context-packs/` — optional example agent configs (not needed to play).
- `index.html`, `app.js`, `styles.css`, `atlas-data.js`, `generate_atlas_data.py` — the visual atlas.

## License

See [`LICENSE`](LICENSE).
