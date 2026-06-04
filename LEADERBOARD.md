# Leaderboard

A community board ranking AI coding setups by how they score on this corpus. **Opt-in.**

- **Ranking:** weighted pass-rate (higher = better). Ties break on fewer tokens, then less time.
  Entries with any `unsafe` change (edits outside `allowed_paths`) are flagged and sorted last.
- **Correctness** is computed by `run.py` from your run.
- **Efficiency** (tokens / time / cost) is **self-reported and unverified**, and depends on your
  provider, hardware, and price — so it is shown as context, not used for ranking.

## Submit an entry

1. Solve a whole eval-set with your setup, scoring each task (`run.py prepare` → solve → `run.py score`).
2. Aggregate + stamp your self-reported numbers in one go:

       python run.py score-set tasks/eval-sets/core.json \
         --agent "My Setup (Cursor + GPT-5)" --model "gpt-5" \
         --seconds 540 --tokens-in 120000 --tokens-out 30000 \
         --emit-entry my-setup

   That writes `leaderboard/entries/my-setup.json`.
3. (Optional, for a re-verifiable entry) include your per-task solution diffs under
   `leaderboard/entries/my-setup.diffs/` so a maintainer can re-run the scorer.
4. Regenerate the board data and open a PR:

       python generate_leaderboard_data.py
       # commit leaderboard/entries/my-setup.json + leaderboard-data.js, then PR

Be honest: run the real scorer, report real numbers. The board labels every entry `self-reported`.
