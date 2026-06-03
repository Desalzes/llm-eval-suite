# Local Background

The rollout system has three kinds of target predicates:

- account age bucket
- region bucket
- product tier bucket

A feature can target one or more values in each predicate family. A rollout slot receives several features. Two features interfere when their target populations overlap heavily.

Raw request volume is easy to measure, but it hides structure. A low-volume feature can still be dangerous if it overlaps the same narrow cohort as many other features. A high-volume feature can be safer if its traffic is spread across cells that other features avoid.

Useful plan qualities:

- Convert a vague idea into a representation where overlap can be checked.
- Prefer candidate families that can be generated and falsified.
- Borrow mechanisms from distant domains only when the borrowed move is named and testable.
- Include negative controls: cases where the proposed route should fail.
- Separate "this is a promising hypothesis" from "this has been proved."

The plan does not need to know the real production schema. It only needs to propose a precise, checkable local research route.
