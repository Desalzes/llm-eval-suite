# Local Background

Each experiment has:

- an estimated request volume
- a set of cohort predicates
- a list of service or feature dependencies

Two experiments conflict when their cohorts overlap heavily or when they share a dependency that cannot tolerate simultaneous rollout pressure.

Greedy-Spread uses only estimated request volume during placement. It does not explicitly color a conflict graph. This creates a possible gap between a true theorem about graph coloring and a false engineering claim about a specific load-greedy algorithm.

Useful construction ideas:

- Conflict graphs where greedy coloring fails under a bad vertex order.
- Equal-volume decoys that steer a load-balancing heuristic into the wrong slot.
- Small gadgets that can be composed into larger adversarial families.
- Solver-backed exhaustive search over tiny instances before scaling to random generators.
- Negative controls where all conflicts are cliques, all volumes are identical, or the graph is already easy to color.

The output is a research plan. It should be specific enough for a follow-up engineer to build the generator and checker, but it should not pretend the counterexample has already been found.
