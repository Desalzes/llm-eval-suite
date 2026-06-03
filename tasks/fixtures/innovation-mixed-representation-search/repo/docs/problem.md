# Rollout Interference Invention Task

You are designing a local research plan for a feature-rollout scheduler.

The current heuristic balances raw request volume across rollout slots. The team is tempted to treat that as enough: if each slot receives roughly the same number of requests, pairwise feature interference should be low.

That default framing is suspicious. Features target correlated cohorts, not anonymous volume. Two rollout slots can have equal raw volume while repeatedly touching the same cohort cells. The goal is to invent a better route for finding, testing, or refuting scheduling strategies.

Create `innovation_plan.json` at the repository root. Do not implement the scheduler. Do not claim a proof. Produce a testable invention plan that a follow-up engineer could turn into a generator, checker, or small search experiment.

Your plan should answer:

- What is the default framing?
- Why might the default framing fail?
- What independent branches should be tried before optimizing one route?
- What remote analogies are worth borrowing from?
- What representation shift could make interference easier to reason about?
- What construction or counterexample search would pressure-test the raw-volume heuristic?
- What certificate, checker, or falsification route would decide whether a candidate is real?

Write only `innovation_plan.json`.
