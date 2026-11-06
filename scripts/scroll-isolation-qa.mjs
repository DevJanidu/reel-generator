import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { mkdir, readFile, writeFile } from "node:fs/promises";
const episode = JSON.parse(
  await readFile("artifacts/workflow-qa/result.json", "utf8"),
).episode;
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
const base = "http://127.0.0.1:5174";
await mkdir("artifacts/scroll-isolation", { recursive: true });
await page.route(`**/api/episodes/${episode}`, async (route) => {
  const response = await route.fetch(),
    body = await response.json();
  const t = new Date().toISOString();
  for (let i = 0; i < 80; i++) {
    body.file_entries.push({
      path: `05_assets/fixture-${String(i).padStart(3, "0")}.txt`,
      kind: "file",
      size_bytes: i,
      modified_at: t,
    });
    body.file_entries.push({
      path: `fixture-folder-${String(i).padStart(3, "0")}`,
      kind: "directory",
      size_bytes: null,
      modified_at: t,
    });
  }
  await route.fulfill({ response, json: body });
});
const sidebar = page.locator("[data-sidebar=content]"),
  main = page.locator("#page-content"),
  left = page.locator(".explorer-sidebar"),
  right = page.locator(".explorer-files [data-slot=scroll-area-viewport]");
const pos = async () =>
  Promise.all(
    [sidebar, main, left, right].map(async (x) =>
      (await x.count()) ? x.evaluate((e) => e.scrollTop) : 0,
    ),
  );
const set = async (el, v) =>
  el.evaluate((e, n) => {
    e.scrollTop = n;
  }, v);
const wheel = async (el, dy) => {
  const b = await el.boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + Math.min(b.height / 2, 150));
  await page.mouse.wheel(0, dy);
  await page.waitForTimeout(200);
};
try {
  await page.goto(base + `/assets?episode=${episode}`);
  await expect(
    page.getByRole("region", { name: "Production status" }),
  ).toBeVisible();
  await expect(
    page.getByText("Generate 3 still images", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("region", { name: "Production status" }),
  ).toBeVisible();
  expect(await sidebar.evaluate((e) => e.scrollHeight > e.clientHeight)).toBe(
    true,
  );
  let before = await pos();
  await wheel(sidebar, 400);
  let after = await pos();
  expect(after[0]).toBeGreaterThan(before[0]);
  expect(after.slice(1)).toEqual(before.slice(1));
  await set(sidebar, 1e6);
  before = await pos();
  await wheel(sidebar, 600);
  after = await pos();
  expect(after).toEqual(before);
  await set(sidebar, 0);
  before = await pos();
  await wheel(sidebar, -600);
  after = await pos();
  expect(after).toEqual(before);
  await set(main, 0);
  before = await pos();
  await wheel(page.locator(".page-heading"), 500);
  after = await pos();
  expect(after[1]).toBeGreaterThan(before[1]);
  expect([after[0], after[2], after[3]]).toEqual([
    before[0],
    before[2],
    before[3],
  ]);
  await page
    .getByRole("button", { name: "Open File Explorer", exact: true })
    .click();
  await page.locator(".file-explorer").waitFor();
  await page.locator(".file-explorer").scrollIntoViewIfNeeded();
  for (const el of [left, right]) {
    expect(await el.evaluate((e) => e.scrollHeight > e.clientHeight)).toBe(
      true,
    );
    await set(el, 0);
    before = await pos();
    await wheel(el, 350);
    after = await pos();
    const index = el === left ? 2 : 3;
    expect(after[index]).toBeGreaterThan(before[index]);
    for (let i = 0; i < 4; i++)
      if (i !== index) expect(after[i]).toBe(before[i]);
    for (const [edge, delta] of [
      [1e6, 600],
      [0, -600],
    ]) {
      await set(el, edge);
      before = await pos();
      await wheel(el, delta);
      after = await pos();
      expect(after).toEqual(before);
    }
  }
  await set(right, 0);
  await right.focus();
  await page.keyboard.press("PageDown");
  await expect
    .poll(() => right.evaluate((e) => e.scrollTop))
    .toBeGreaterThan(0);
  await page.screenshot({ path: "artifacts/scroll-isolation/desktop.png" });
  for (const [width, height] of [
    [1920, 1080],
    [1440, 900],
    [1366, 768],
    [1024, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      String(width),
    ).toBe(false);
    await expect(page.locator(".file-explorer")).toBeVisible();
    await page.screenshot({ path: `artifacts/scroll-isolation/${width}.png` });
  }
  await writeFile(
    "artifacts/scroll-isolation/result.json",
    JSON.stringify(
      {
        passed: true,
        overflowFixtures:
          "80 folders and 80 files injected into read-only API response",
        checks: [
          "sidebar movement and boundary isolation",
          "main movement alone",
          "both explorer panes move independently and contain top/bottom wheel",
          "production status open after refresh",
          "desktop and mobile widths",
        ],
      },
      null,
      2,
    ),
  );
  console.log(
    "PASS: real wheel movement, both boundaries, expanded status and five viewport widths",
  );
} finally {
  await browser.close();
}
