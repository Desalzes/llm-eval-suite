# Cloud Deploy Skill Reference Selection Contract

This fixture models a common skill-authoring mistake: a multi-provider skill pastes every provider guide into `SKILL.md`. The corrected skill must keep only provider selection and shared workflow guidance in `SKILL.md`, then link to provider-specific references that should be read only when relevant.

## Required Shape

- Editable files are limited to:
  - `skills/cloud-deploy/SKILL.md`
  - `skills/cloud-deploy/references/aws.md`
  - `skills/cloud-deploy/references/gcp.md`
  - `skills/cloud-deploy/references/azure.md`
- `SKILL.md` must start with YAML frontmatter containing only `name` and `description`.
- `name` must be `cloud-deploy`.
- `description` must start with `Use when` and describe cloud deployment trigger conditions only.
- The description must not summarize provider commands or provider-specific workflow steps.

## Body Requirements

`SKILL.md` should be concise and procedural. It must cover:

- identifying the target provider,
- confirming runtime, service shape, region, secrets, rollout strategy, and rollback needs,
- reading only the relevant provider reference from `references/aws.md`, `references/gcp.md`, or `references/azure.md`,
- avoiding provider-specific commands in `SKILL.md`,
- verifying health checks, logs, configuration, and rollback before finishing.

Provider-specific commands, IAM or identity notes, logging locations, and rollout checks belong in the matching reference file.

## Reference Requirements

Each reference file must contain concrete provider-specific deployment guidance:

- `references/aws.md`: AWS ECS or App Runner commands, IAM, CloudWatch, health checks, and rollback.
- `references/gcp.md`: Cloud Run or App Engine commands, service accounts, Cloud Logging, health checks, and rollback.
- `references/azure.md`: Azure Web App or Container Apps commands, managed identity, Application Insights, health checks, and rollback.

## Style Requirements

- Avoid vague filler such as "deploy it somehow", "handle cloud appropriately", and "etc.".
- Do not add README, changelog, quick reference, or installation docs.
