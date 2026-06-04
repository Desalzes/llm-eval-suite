# Leaderboard

A community board ranking AI coding setups by how they score on this corpus. **Opt-in.**

Every entry is attributed to a **setup** — the instructions, skills, and context the agent ran
with — because the benchmark scores an *agent + model + setup*, not just a model name. A setup
should describe what was actually used, so a score is reproducible. Legacy rows that predate custom
setups use `agentic-default` (a default agentic run with no custom skills/instructions).

- **Ranking:** weighted pass-rate (higher = better). Ties break on fewer tokens, then less time.
  Entries with any `unsafe` change (edits outside `allowed_paths`) are flagged and sorted last.
- **Correctness** is computed by `run.py` from your run.
- **Efficiency** (tokens / time / cost) is **self-reported and unverified**, and depends on your
  provider, hardware, and price — so it is shown as context, not used for ranking.

## Submit an entry

1. Solve a whole eval-set with your setup, scoring each task (`run.py prepare` → solve → `run.py score`).
2. Aggregate + stamp your self-reported numbers in one go. **`--setup` is required** — every
   entry must declare the setup that produced it (the board links each score back to its setup):

       python run.py score-set tasks/eval-sets/core.json \
         --agent "My Setup (Cursor + GPT-5)" --model "gpt-5" \
         --setup my-setup \
         --seconds 540 --tokens-in 120000 --tokens-out 30000 \
         --emit-entry my-setup

   That writes `leaderboard/entries/my-setup.json`. The `--setup` value should be a setup id under
   `setups/` (run `python run.py setup new <name>` to create one). Entries without a setup are
   skipped when the board is built.
3. (Optional, for a re-verifiable entry) include your per-task solution diffs under
   `leaderboard/entries/my-setup.diffs/` so a maintainer can re-run the scorer.
4. Regenerate the board data and open a PR:

       python generate_leaderboard_data.py
       # commit leaderboard/entries/my-setup.json + leaderboard-data.js, then PR

Be honest: run the real scorer, report real numbers. The board labels every entry `self-reported`.
