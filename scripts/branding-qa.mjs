import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { mkdir, writeFile } from "node:fs/promises";
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const context = await browser.newContext();
const page = await context.newPage();
const failures = [];
page.on("pageerror", (e) => failures.push(e.message));
await mkdir("artifacts/branding", { recursive: true });
try {
  for (const [width, height] of [
    [1920, 1080],
    [1366, 768],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto("http://127.0.0.1:5174/");
    const logo = page.locator(".sidebar-brand-mark"),
      header = page.locator(".app-sidebar-header"),
      copy = page.locator(".sidebar-brand-copy");
    await expect(logo).toBeVisible();
    await expect(copy).toBeVisible();
    expect(await logo.evaluate((e) => e.complete && e.naturalWidth > 0)).toBe(
      true,
    );
    const links = await page
      .locator('link[rel~="icon"]')
      .evaluateAll((nodes) => nodes.map((n) => n.href));
    expect(links.some((x) => x.includes("favicon.svg?v=of1"))).toBe(true);
    expect((await page.request.get(links[0])).status()).toBe(200);
    expect(
      (
        await page.request.get("http://127.0.0.1:5174/favicon.ico?v=of1")
      ).status(),
    ).toBe(200);
    await expect(page).toHaveTitle("ODD FRAME — Reel Workflow Station");
    await header.screenshot({
      path: `artifacts/branding/expanded-${width}.png`,
    });
    const initial = await logo.boundingBox();
    await page.getByRole("button", { name: "Toggle Sidebar" }).click();
    await expect(copy).not.toBeVisible();
    await expect
      .poll(async () => Math.round((await header.boundingBox()).width))
      .toBe(47);
    const collapsed = await logo.boundingBox(),
      h = await header.boundingBox();
    expect(collapsed.width).toBe(36);
    expect(collapsed.height).toBe(36);
    expect(collapsed.x).toBeGreaterThanOrEqual(h.x);
    expect(collapsed.x + collapsed.width).toBeLessThanOrEqual(h.x + h.width);
    expect(
      Math.abs(collapsed.x + collapsed.width / 2 - (h.x + h.width / 2)),
    ).toBeLessThanOrEqual(1);
    expect(Math.abs(collapsed.x - initial.x)).toBeLessThanOrEqual(1);
    await header.screenshot({
      path: `artifacts/branding/collapsed-${width}.png`,
    });
    await page
      .getByRole("link", { name: "Ideas", exact: true })
      .and(page.locator("a"))
      .hover();
    await expect(
      page.getByRole("tooltip", { name: "Ideas", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Toggle Sidebar" }).click();
    await expect(copy).toBeVisible();
    await expect
      .poll(async () => Math.abs((await logo.boundingBox()).x - initial.x))
      .toBeLessThanOrEqual(1);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Toggle Sidebar" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const mobileLogo = dialog.locator(".sidebar-brand-mark"),
    mobileHeader = dialog.locator(".app-sidebar-header");
  await expect(mobileLogo).toBeVisible();
  const m = await mobileLogo.boundingBox(),
    h = await mobileHeader.boundingBox();
  expect(m.x).toBeGreaterThanOrEqual(h.x);
  expect(m.x + m.width).toBeLessThanOrEqual(h.x + h.width);
  await page.screenshot({ path: "artifacts/branding/mobile.png" });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  expect(failures).toEqual([]);
  await writeFile(
    "artifacts/branding/result.json",
    JSON.stringify(
      {
        passed: true,
        checks: [
          "SVG and ICO return HTTP 200",
          "Correct page title",
          "1920 and 1366 expanded/collapsed logo bounds and centered alignment",
          "No logo position shift",
          "Collapsed tooltip",
          "390px mobile Sheet",
        ],
        failures,
      },
      null,
      2,
    ),
  );
  console.log(
    "PASS: favicon resources, title, sidebar geometry, transitions and mobile",
  );
} finally {
  await browser.close();
}
