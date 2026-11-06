import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { readFile, writeFile, mkdir } from "node:fs/promises";
const base = "http://127.0.0.1:5174";
const store = new URL("../artifacts/preview-data/", import.meta.url);
const token = JSON.parse(
  await readFile(new URL("data/controller-access.json", store), "utf8"),
).token;
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await mkdir("artifacts/new-ui", { recursive: true });
const routes = {
  Home: "/",
  "Master Prompt": "/master-prompt",
  Ideas: "/ideas",
  "Script Studio": "/script",
  "Episode Workspace": "/workspace",
  "Google Flow Prompts": "/flow",
  "Asset Manager": "/assets",
  "Edit Studio": "/studio",
  Exports: "/exports",
  Analytics: "/analytics",
  Settings: "/settings",
  "Production Queue": "/queue",
  "AI Activity": "/activity",
  "System Health": "/health",
  "How to Use": "/help",
};
const checks = [];
try {
  await page.goto(base + "/#controller=" + token);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  for (const [name, path] of Object.entries(routes)) {
    await page
      .getByRole("link", { name, exact: true })
      .and(page.locator("a"))
      .click();
    await expect(page).toHaveURL(base + path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `artifacts/new-ui/${name.replaceAll(" ", "-")}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      name + " desktop overflow",
    ).toBe(false);
    checks.push(name + " route and desktop layout");
  }
  await page.reload();
  await expect(
    page.getByRole("heading", { level: 1, name: "How to Use" }),
  ).toBeVisible();
  await page.getByLabel("Search help").fill("approval");
  await expect(
    page.getByRole("button", { name: /Approve a script/ }),
  ).toBeVisible();
  const helpTrigger = page.getByRole("button", { name: /Approve a script/ });
  expect(
    await helpTrigger.evaluate((el) => getComputedStyle(el).backgroundColor),
  ).toBe("rgba(0, 0, 0, 0)");
  await helpTrigger.click();
  await expect(helpTrigger).toHaveAttribute("aria-expanded", "true");
  await expect
    .poll(() =>
      page
        .locator("[data-slot=accordion-content][data-state=open]")
        .first()
        .evaluate((el) => el.clientHeight),
    )
    .toBeGreaterThan(100);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "artifacts/new-ui/help-open.png",
    fullPage: true,
  });
  checks.push(
    "Neutral Help accordion, subtle open state and readable expanded content",
  );
  await page.goBack();
  await expect(page).toHaveURL(base + "/health");
  await page.goForward();
  await expect(page).toHaveURL(base + "/help");
  checks.push("Refresh and browser back/forward");
  await page.goto(base + "/queue");
  const reelButton = page.getByRole("button", { name: /^OF_R\d+/ }).first();
  await expect(reelButton).toBeVisible();
  const reelStyle = await reelButton.evaluate((el) => ({
    color: getComputedStyle(el).color,
    background: getComputedStyle(el).backgroundColor,
  }));
  expect(reelStyle.background).toBe("rgba(0, 0, 0, 0)");
  const primaryStyle = await page
    .getByRole("button", { name: "Create New Reel", exact: true })
    .evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(primaryStyle).toBe("rgb(229, 229, 229)");
  const navItems = page
    .locator('[data-slot="sidebar-menu"]')
    .first()
    .locator("a");
  const firstBox = await navItems.nth(0).boundingBox(),
    secondBox = await navItems.nth(1).boundingBox();
  expect(secondBox.y - firstBox.y - firstBox.height).toBeGreaterThanOrEqual(6);
  await page
    .getByRole("link", { name: "AI Activity", exact: true })
    .and(page.locator("a"))
    .hover();
  await page.screenshot({
    path: "artifacts/new-ui/queue-hover.png",
    fullPage: true,
  });
  checks.push(
    "Visible Reel link labels, neutral primary buttons and 6px sidebar hover gaps",
  );
  await page.goto(base + "/help");

  await page.getByRole("button", { name: "Toggle Sidebar" }).click();
  await page.reload();
  expect(await page.evaluate(() => localStorage.getItem("odd-sidebar"))).toBe(
    "collapsed",
  );
  await page
    .getByRole("link", { name: "Ideas", exact: true })
    .and(page.locator("a"))
    .hover();
  await expect(
    page.getByRole("tooltip", { name: "Ideas", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Toggle Sidebar" }).click();
  checks.push("Sidebar preference and collapsed tooltip");
  const fixtureEpisode = JSON.parse(
    await readFile("artifacts/workflow-qa/result.json", "utf8"),
  ).episode;
  for (const route of [
    "/script",
    "/workspace",
    "/flow",
    "/assets",
    "/studio",
  ]) {
    await page.goto(base + route + "?episode=" + fixtureEpisode);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByLabel("Active Reel", { exact: true })).toHaveValue(
      String(fixtureEpisode),
    );
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: "artifacts/new-ui/" + route.slice(1) + "-populated.png",
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [name, path] of Object.entries(routes)) {
    await page.goto(base + path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `artifacts/new-ui/${name.replaceAll(" ", "-")}-mobile.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      name + " mobile overflow",
    ).toBe(false);
  }
  await page.getByRole("button", { name: "Toggle Sidebar" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("link", { name: "Ideas", exact: true })
    .and(page.locator("a"))
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page).toHaveURL(base + "/ideas");
  checks.push("Mobile Sheet navigation and every route layout");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: /AI Activity,/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  checks.push("Activity Sheet Escape");
  await page.goto(base + "/health");
  await page.route("**/api/status", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Disposable outage fixture" }),
    }),
  );
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Retry connection", exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await page.unroute("**/api/status");
  await page
    .getByRole("button", { name: "Retry connection", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Retry connection", exact: true }),
  ).not.toBeVisible();
  checks.push("Request failure and explicit retry recovery");
  const crossOrigin = await fetch(base + "/api/settings", {
    method: "PUT",
    headers: {
      "content-type": "application/json",
      "x-odd-controller": token,
      origin: "https://example.com",
    },
    body: JSON.stringify({ provider: "manual" }),
  });
  expect(crossOrigin.status).toBe(403);
  checks.push("Cross-origin mutation protection preserved");
  expect(errors).toEqual([]);
  await writeFile(
    "artifacts/new-ui/result.json",
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, checks, errors }, null, 2));
} catch (e) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "artifacts/new-ui/failure.png",
    fullPage: true,
  });
  throw e;
} finally {
  await browser.close();
}
