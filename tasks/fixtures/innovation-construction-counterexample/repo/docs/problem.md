# Greedy-Spread Counterexample Search

The rollout team proposes a universal scheduling rule:

> Sort experiments by estimated request volume. For each experiment, assign it to the rollout slot with the lowest current raw volume. If there are `max_conflict_degree + 1` slots, this Greedy-Spread rule should avoid dangerous conflict concentration.

The claim is plausible because it echoes a familiar graph-coloring intuition: a graph with maximum degree `d` can be colored with `d + 1` colors. But the actual rule is not graph coloring. It uses request volume order and lowest-load placement, while conflicts come from shared cohorts and service dependencies.

Create `innovation_plan.json` at the repository root. Do not implement the scheduler. Do not claim a proof or disproof. Draft a construction-focused invention plan that tries to find, shrink, and certify a counterexample family for Greedy-Spread.

The plan should answer:

- What exactly is the default greedy claim?
- Why might it be false even if the `d + 1` coloring intuition is true?
- What adversarial construction families should be generated?
- What representation shift makes the claim checkable?
- What brute-force, SAT, ILP, or property-test checker would certify a counterexample?
- What negative controls should pass if the checker is honest?
- What would count as falsifying or supporting the claim?

Write only `innovation_plan.json`.
