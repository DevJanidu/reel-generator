import { chromium } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile, readFile } from "node:fs/promises";
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const results = [];
let episode;
try {
  episode = JSON.parse(
    await readFile("artifacts/workflow-qa/result.json", "utf8"),
  ).episode;
} catch {}
await mkdir("artifacts/accessibility", { recursive: true });
try {
  for (const route of [
    "/",
    "/ideas",
    "/script",
    "/workspace",
    "/flow",
    "/assets",
    "/studio",
    "/exports",
    "/analytics",
    "/settings",
    "/queue",
    "/activity",
    "/health",
    "/help",
  ]) {
    await page.goto(
      "http://127.0.0.1:5174" + route + (episode ? "?episode=" + episode : ""),
    );
    await page.getByRole("heading", { level: 1 }).waitFor();
    await page
      .locator('[role="status"][aria-label="Loading station"]')
      .waitFor({ state: "hidden" });
    if (route === "/help")
      await page.getByRole("button", { name: /Approve a script/ }).click();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    results.push({
      route,
      violations: result.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
    });
  }
  await writeFile(
    "artifacts/accessibility/result.json",
    JSON.stringify(results, null, 2),
  );
  console.log(
    JSON.stringify(
      results.filter((r) => r.violations.length),
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
