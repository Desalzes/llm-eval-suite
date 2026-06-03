# Progressive Disclosure Skill Contract

This fixture checks whether a draft skill can be refactored into a concise, triggerable skill with detailed material moved into a reference file.

## Required Files

- `skills/browser-testing/SKILL.md`
- `skills/browser-testing/references/playwright.md`

Do not add README files, quick-reference files, or changelogs.

## SKILL.md Requirements

- Frontmatter must include `name: browser-testing`.
- The description must start with `Use when`.
- The description must only describe triggering conditions, not workflow steps.
- The body should stay concise and point to `references/playwright.md` for details.
- The body must include a short workflow and a "When to Use" section.

## Reference Requirements

`references/playwright.md` should hold the detailed Playwright examples that do not belong in the main skill body.

It must mention:

- `page.goto`
- `locator`
- `expect`
- `screenshot`
- `trace`

## Style Requirements

- Keep `SKILL.md` under 350 words.
- Keep the reference file over 120 words so it is not just a stub.
- Avoid vague filler such as "etc." or "handle appropriately".
