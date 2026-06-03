import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Locator } from "@playwright/test";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const baselineDir = path.join(__dirname, "baselines");

async function expectLocatorToMatchBaseline(
  locator: Locator,
  baselineName: string,
  maxDiffRatio = 0.01
) {
  const actualBuffer = await locator.screenshot({
    animations: "disabled"
  });
  const baselinePath = path.join(baselineDir, baselineName);
  const expected = PNG.sync.read(fs.readFileSync(baselinePath));
  const actual = PNG.sync.read(actualBuffer);

  expect(
    { width: actual.width, height: actual.height },
    `${baselineName} dimensions changed`
  ).toEqual({ width: expected.width, height: expected.height });

  const diff = new PNG({ width: expected.width, height: expected.height });
  const differentPixels = pixelmatch(
    actual.data,
    expected.data,
    diff.data,
    expected.width,
    expected.height,
    { threshold: 0.12 }
  );
  const diffRatio = differentPixels / (expected.width * expected.height);

  expect(
    diffRatio,
    `${baselineName} diff ratio ${diffRatio.toFixed(4)} exceeded ${maxDiffRatio}`
  ).toBeLessThanOrEqual(maxDiffRatio);
}

test.describe("filter-bar visual regression", () => {
  test("filter-bar tablet layout matches the approved visual baseline", async ({
    page
  }) => {
    await page.setViewportSize({ width: 820, height: 720 });
    await page.goto("/");

    const frame = page.getByTestId("filter-bar-visual-frame");
    await expect(frame).toBeVisible();
    await expectLocatorToMatchBaseline(frame, "filter-bar-tablet.png");
  });

  test("filter-bar active state remains visible in high-contrast mode", async ({
    page
  }) => {
    await page.setViewportSize({ width: 820, height: 720 });
    await page.emulateMedia({ forcedColors: "active" });
    await page.goto("/");

    const frame = page.getByTestId("filter-bar-visual-frame");
    await expect(frame).toBeVisible();

    const activeStatus = page.getByRole("radio", { name: "In Review" });
    await expect(activeStatus).toHaveAttribute("aria-checked", "true");

    const activeIndicator = await activeStatus.evaluate((element) => {
      const styles = getComputedStyle(element);

      return {
        outlineStyle: styles.outlineStyle,
        outlineWidth: Number.parseFloat(styles.outlineWidth)
      };
    });

    expect(activeIndicator.outlineStyle).not.toBe("none");
    expect(activeIndicator.outlineWidth).toBeGreaterThanOrEqual(2);

    await expectLocatorToMatchBaseline(frame, "filter-bar-high-contrast.png", 0.015);
  });
});
