# Skill-effect A/B

Run the same Trial twice with two setups that differ only by a skill, then pair the
results into a shareable delta. It answers "does adding skill X actually help?" — on real,
restraint-gated fixtures, not toy snippets.

## Run it

    python run.py trial prepare trials/trial-1.json
    # solve every objective with YOUR agent under the baseline setup, then:
    python run.py trial score trials/trial-1.json --setup agentic-default --emit-entry base-trial1
    # re-solve under baseline + the skill, then:
    python run.py trial score trials/trial-1.json --setup ponytail --emit-entry pony-trial1
    python run.py trial ab --trial trial-1 --baseline agentic-default --treatment ponytail

This writes `leaderboard/ab/trial-ab-trial-1-agentic-default-vs-ponytail.json` plus a
self-contained `.svg` badge and a `.md` one-liner.

## Rules

- The two setups must differ ONLY by the skill, so the delta is attributable.
- Both setups must be general — `trial ab` refuses to pair if a setup's text mentions a
  challenge id (no smuggled answers).
- Restraint is per arm: if the skill induces an out-of-`allowed_paths` edit, that arm is
  capped at 50 and the result flags it.
- Single run is `n=1` (labeled). Statistical CI is deferred.

## The trial-ab.json contract

`{ schema, trial_id, baseline{setup_id,trial_score,weighted_pass_rate,flagged_unsafe,by_category},
treatment{...}, delta{overall, by_category:[{category,lift}], restraint}, runs_per_arm, generated_at }`.
`restraint` is one of `both_clean | treatment_violated | baseline_violated | both_violated`.
