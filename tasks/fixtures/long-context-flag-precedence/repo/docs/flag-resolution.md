# Feature Flag Resolution

Flag decisions are loaded from JSON files in the `configs/` directory. The resolver must preserve explicit `false` values because disabling a rollout is an intentional decision.

## Precedence

Use the first configured value found in this order:

1. `users.json` for the specific `user_id`.
2. `cohorts.json` for the supplied `cohort`.
3. `environment.json` for the current environment.
4. `defaults.json` for the global fallback.

If no file contains the flag, return `enabled: false` and `source: "implicit_default"`.

## Return Shape

Return a dictionary with:

- `flag`: the requested flag name.
- `enabled`: the resolved boolean decision.
- `source`: one of `user`, `cohort`, `environment`, `default`, or `implicit_default`.
