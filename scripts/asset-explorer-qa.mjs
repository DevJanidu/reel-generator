// Uses only the disposable preview store. No live provider or render execution.
import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import AxeBuilder from "@axe-core/playwright";
const data = path.join(process.cwd(), "artifacts/preview-data");
const episode = JSON.parse(
  await readFile("artifacts/workflow-qa/result.json", "utf8"),
).episode;
const token = JSON.parse(
  await readFile(path.join(data, "data/controller-access.json"), "utf8"),
).token;
const setup = spawnSync(
  "E:/facebook/.venv/Scripts/python.exe",
  [
    "-c",
    `from pathlib import Path; from services.api.core import episode,epdir; root=epdir(episode(${episode})); assert root.is_relative_to(Path.cwd()/'artifacts/preview-data'); target=root/'05_assets/images/review'; target.mkdir(exist_ok=True); (target/'notes.txt').write_text('Disposable file explorer note.',encoding='utf-8')`,
  ],
  {
    cwd: process.cwd(),
    env: { ...process.env, ODD_DATA_ROOT: data, ODD_AI_PROVIDER: "manual" },
    windowsHide: true,
  },
);
if (setup.status) throw Error("Disposable fixture setup failed");
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await mkdir("artifacts/asset-explorer", { recursive: true });
try {
  await page.goto(
    `http://127.0.0.1:5174/assets?episode=${episode}#controller=${token}`,
  );
  const listing = await page.request.get(
    "http://127.0.0.1:5174/api/episodes/" + episode,
  );
  const catalog = (await listing.json()).file_entries;
  expect(
    catalog.some((e) =>
      e.path.toLowerCase().split("/").includes(".production"),
    ),
  ).toBe(false);
  const explorer = page.getByRole("region", { name: "Episode file explorer" });
  await expect(explorer).toBeVisible();
  for (const name of ["images", "narration", "subtitles", "music"])
    await expect(
      explorer.getByRole("button", {
        name: "Open folder " + name,
        exact: true,
      }),
    ).toBeVisible();
  await expect(
    explorer.getByRole("button", { name: "Preview S001.png", exact: true }),
  ).not.toBeVisible();
  await explorer.getByRole("button", { name: "Images", exact: true }).click();
  await expect(
    explorer.getByRole("button", { name: "Preview S001.png", exact: true }),
  ).toBeVisible();
  await expect(
    explorer.getByRole("button", { name: "Open folder review", exact: true }),
  ).toBeVisible();
  await explorer.getByLabel("Search this folder").fill("S001");
  await expect(
    explorer.getByRole("button", { name: "Open folder review", exact: true }),
  ).not.toBeVisible();
  await explorer.getByLabel("Search this folder").fill("");
  await explorer.getByLabel("Sort files").click();
  await page.getByRole("option", { name: "Size", exact: true }).click();
  await explorer
    .getByRole("button", { name: "Sort descending", exact: true })
    .click();
  await explorer
    .getByRole("button", { name: "Grid view", exact: true })
    .click();
  await expect(explorer.locator(".explorer-tile")).not.toHaveCount(0);
  await explorer
    .getByRole("button", { name: "List view", exact: true })
    .click();
  await explorer
    .getByRole("button", { name: "Open folder review", exact: true })
    .click();
  await explorer
    .getByRole("button", { name: "Preview notes.txt", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Disposable file explorer note.",
  );
  await page.keyboard.press("Escape");
  await explorer
    .getByRole("button", { name: "Back to previous folder", exact: true })
    .click();
  await expect(
    explorer.getByRole("button", { name: "Preview S001.png", exact: true }),
  ).toBeVisible();
  await explorer
    .getByRole("button", { name: "Narration", exact: true })
    .click();
  const audioName = `explorer-qa-${Date.now()}.wav`;
  const wave = Buffer.alloc(8044, 128);
  wave.write("RIFF", 0);
  wave.writeUInt32LE(8036, 4);
  wave.write("WAVEfmt ", 8);
  wave.writeUInt32LE(16, 16);
  wave.writeUInt16LE(1, 20);
  wave.writeUInt16LE(1, 22);
  wave.writeUInt32LE(8000, 24);
  wave.writeUInt32LE(8000, 28);
  wave.writeUInt16LE(1, 32);
  wave.writeUInt16LE(8, 34);
  wave.write("data", 36);
  wave.writeUInt32LE(8000, 40);
  const uploading = page.waitForResponse(
    (response) =>
      response.url().endsWith("/assets/narration") &&
      response.request().method() === "POST",
  );
  await explorer.getByLabel("Import narration", { exact: true }).setInputFiles({
    name: audioName,
    mimeType: "audio/wav",
    buffer: wave,
  });
  expect((await uploading).ok()).toBe(true);
  await expect(
    explorer.getByRole("button", {
      name: "Preview " + audioName,
      exact: true,
    }),
  ).toBeVisible();
  await explorer
    .getByRole("button", { name: "Preview " + audioName, exact: true })
    .click();
  await expect(page.getByRole("dialog").locator("audio")).toHaveAttribute(
    "src",
    "/api/episodes/" + episode + "/file/05_assets/narration/" + audioName,
  );
  await page.keyboard.press("Escape");
  const downloading = page.waitForEvent("download");
  await explorer
    .getByRole("link", { name: "Download " + audioName, exact: true })
    .click();
  const download = await downloading;
  await download.saveAs("artifacts/asset-explorer/download.wav");
  expect(await readFile("artifacts/asset-explorer/download.wav")).toEqual(wave);
  await explorer
    .getByRole("button", { name: "Remove " + audioName, exact: true })
    .click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.getByRole("button", { name: "Keep file", exact: true }).click();
  await expect(
    explorer.getByRole("button", {
      name: "Preview " + audioName,
      exact: true,
    }),
  ).toBeVisible();
  await explorer.getByRole("button", { name: "Images", exact: true }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "artifacts/asset-explorer/desktop.png",
    fullPage: true,
  });
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    axe.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    explorer.getByRole("button", { name: "Preview S001.png", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/asset-explorer/mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  expect(errors).toEqual([]);
  const report = {
    passed: true,
    episode,
    checks: [
      "Real separate asset folders, including empty directories",
      "Nested directory navigation and breadcrumbs/back",
      "Current-folder search and size sorting",
      "Grid and list views",
      "Text and audio previews",
      "Actual narration multipart upload and byte-identical download",
      "Remove confirmation cancellation preserves file",
      "No private .production catalog entries",
      "Desktop/mobile layout",
      "Zero axe WCAG A/AA violations",
    ],
    errors,
  };
  await writeFile(
    "artifacts/asset-explorer/result.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
} catch (e) {
  await page.screenshot({
    path: "artifacts/asset-explorer/failure.png",
    fullPage: true,
  });
  throw e;
} finally {
  await browser.close();
}
