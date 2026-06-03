# Relay Handoff: WEATHER

scope_marker: `MASTER: WEATHER`
project: `Weather Betting Markets`

## Hard Rules

- Start user-visible responses with MASTER: WEATHER.
- Keep .claude read-only unless explicitly scoped.

## Source Boundaries

- Root suite source is C:/Users/desal/ChatGPT.
- Weather project pack descriptor exists locally.

## Changed Files

- Several relay and master-session files changed.

## Unresolved Risks

- Project-pack handoff notes may be absent.

## Next Action

Add a relay runner later.

## Verification Evidence

- Tests were run.

## Project Pack Authority Reads

- project_pack AGENTS.md status=present required=true
