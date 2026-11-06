import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const token = JSON.parse(
  await readFile("artifacts/preview-data/data/controller-access.json", "utf8"),
).token;
const episode = JSON.parse(
  await readFile("artifacts/workflow-qa/result.json", "utf8"),
).episode;
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await mkdir("artifacts/layout-polish", { recursive: true });
const checks = [];
try {
  await page.goto("http://127.0.0.1:5174/#controller=" + token);
  await expect(page.locator(".episode-row").first()).toBeVisible();
  for (const row of await page.locator(".episode-row").all()) {
    await row.hover();
    await expect(row).toHaveCSS("background-color", "rgb(41, 41, 41)");
    await expect(row).toHaveCSS("color", "rgb(245, 245, 245)");
  }
  const status = page.locator(".top-status");
  const badge = await status.locator("[data-slot=badge]").boundingBox(),
    provider = await status.locator(".header-provider").boundingBox();
  expect(provider.x - badge.x - badge.width).toBeGreaterThanOrEqual(12);
  const brand = page.locator(".sidebar-brand"),
    mark = page.locator(".sidebar-brand-mark"),
    copy = page.locator(".sidebar-brand-copy");
  const markBox = await mark.boundingBox(),
    copyBox = await copy.boundingBox();
  expect(copyBox.x - markBox.x - markBox.width).toBeGreaterThanOrEqual(12);
  await page.locator(".episode-row").first().hover();
  await page.screenshot({
    path: "artifacts/layout-polish/home-hover.png",
    fullPage: true,
  });
  checks.push(
    "Recent Reel and next-action hovers stay neutral with readable text; header status gap >=12px; expanded logo does not overlap",
  );
  await page.getByRole("button", { name: "Toggle Sidebar" }).click();
  await expect(copy).not.toBeVisible();
  await expect
    .poll(async () => {
      const a = await mark.boundingBox(),
        b = await page.locator(".app-sidebar-header").boundingBox();
      return a.x >= b.x && a.x + a.width <= b.x + b.width;
    })
    .toBe(true);
  await page.screenshot({
    path: "artifacts/layout-polish/collapsed-sidebar.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Toggle Sidebar" }).click();
  await expect(copy).toBeVisible();
  checks.push("Collapsed logo fits within the icon sidebar");
  await page.goto("http://127.0.0.1:5174/ideas");
  const saved = page.getByLabel("Saved story sessions");
  await expect(saved).toBeVisible();
  const session = await saved
    .locator("option")
    .evaluateAll((nodes) => nodes.map((n) => n.value).find(Boolean));
  await saved.selectOption(session);
  const batch = page.getByLabel("Generation batch");
  await expect(batch).toBeVisible();
  for (const select of [saved, batch]) {
    const gap = await select.evaluate((el) => {
      const label = el.closest("label");
      const text = [...label.childNodes].find(
        (n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim(),
      );
      const range = document.createRange();
      range.selectNodeContents(text);
      return (
        el.getBoundingClientRect().top - range.getBoundingClientRect().bottom
      );
    });
    expect(gap).toBeGreaterThanOrEqual(8);
  }
  checks.push("Saved-session and generation-batch label/control gaps >=8px");
  await page.goto(`http://127.0.0.1:5174/workspace?episode=${episode}`);
  const history = page.getByRole("heading", {
    name: "Production history",
    exact: true,
  });
  const search = page.getByPlaceholder("Search production history");
  await expect(search).toBeVisible();
  const h = await history.boundingBox(),
    s = await search.boundingBox();
  expect(s.y - h.y - h.height).toBeGreaterThanOrEqual(12);
  checks.push("Production history heading and search field have a real gap");
  const anonymous = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  const health = await anonymous.newPage();
  await health.goto("http://127.0.0.1:5174/health");
  const alert = health
    .getByRole("alert")
    .filter({ hasText: "This browser window is not authorized" });
  await expect(alert).toBeVisible();
  const alertBox = await alert.boundingBox(),
    headingBox = await health.locator(".page-heading").boundingBox(),
    cardBox = await health
      .getByText("Production foundation", { exact: true })
      .locator('xpath=ancestor::*[@data-slot="card"]')
      .boundingBox();
  expect(alertBox.y - headingBox.y - headingBox.height).toBeGreaterThanOrEqual(
    16,
  );
  expect(cardBox.y - alertBox.y - alertBox.height).toBeGreaterThanOrEqual(16);
  const top = await health.locator(".topbar").boundingBox();
  expect(headingBox.y - top.y - top.height).toBeLessThan(80);
  await health.screenshot({
    path: "artifacts/layout-polish/health-alert.png",
    fullPage: true,
  });
  const axe = await new AxeBuilder({ page: health })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    axe.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  checks.push(
    "Authorization alert has top/bottom spacing and precedes content; short pages align to top; axe passes",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("http://127.0.0.1:5174/");
  await page.screenshot({
    path: "artifacts/layout-polish/mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  await page.getByRole("button", { name: "Toggle Sidebar" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  const mobileMark = await mark.boundingBox(),
    mobileCopy = await copy.boundingBox();
  expect(mobileCopy.x - mobileMark.x - mobileMark.width).toBeGreaterThanOrEqual(
    12,
  );
  checks.push("Mobile layout and sidebar logo spacing pass");
  expect(errors).toEqual([]);
  await writeFile(
    "artifacts/layout-polish/result.json",
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, checks, errors }, null, 2));
} catch (e) {
  await page.screenshot({
    path: "artifacts/layout-polish/failure.png",
    fullPage: true,
  });
  throw e;
} finally {
  await browser.close();
}
