---
name: Browser Testing
description: Use when testing a browser UI by opening pages, navigating, clicking controls, checking screenshots, recording traces, debugging selectors, making assertions, and writing Playwright tests.
---

# Browser Testing

Use this for browser testing.

## Steps

First open the page with Playwright. Use `page.goto("http://localhost:3000")` and wait for the page. Use `page.locator("button")` to find buttons. Use `locator.click()` to click. Use `locator.fill("hello")` to type. Use `expect(locator).toBeVisible()` to assert visibility. Use `expect(locator).toHaveText("Saved")` to check text. Use `page.screenshot({ path: "screenshot.png", fullPage: true })` for screenshots. Use trace recording when debugging complicated flows. Use `context.tracing.start({ screenshots: true, snapshots: true })`, then run the test, then use `context.tracing.stop({ path: "trace.zip" })`.

For navigation tests, use `page.goto`, then click links, then expect the URL. For forms, use locator fill and submit. For dialogs, attach dialog handlers. For network behavior, use route interception. For flaky tests, increase timeouts. For mobile, set viewport. For hover, use locator hover. For keyboard, use page keyboard. For screenshots, compare baselines. For debugging, use headed mode. For trace, use Playwright trace viewer. For selectors, prefer roles, labels, and test ids. For iframes, use frame locators. For downloads, wait for download events. For popups, wait for popup events.

Keep doing the appropriate browser checks etc.
