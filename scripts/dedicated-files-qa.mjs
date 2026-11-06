import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { readFile, writeFile, mkdir } from "node:fs/promises";
const episode = JSON.parse(
    await readFile("artifacts/workflow-qa/result.json", "utf8"),
  ).episode,
  token = JSON.parse(
    await readFile(
      "artifacts/preview-data/data/controller-access.json",
      "utf8",
    ),
  ).token;
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await mkdir("artifacts/dedicated-files", { recursive: true });
try {
  await page.goto(
    `http://127.0.0.1:5174/assets?episode=${episode}#controller=${token}`,
  );
  await expect(
    page.getByRole("region", { name: "Production status" }),
  ).toBeVisible();
  await expect(page.locator(".file-explorer")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Open File Explorer", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`/episodes/${episode}/files`));
  await expect(page.locator(".file-explorer")).toBeVisible();
  await page.reload();
  await expect(page.locator(".file-explorer")).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("button", { name: "Open File Explorer", exact: true }),
  ).toBeVisible();
  await page.goForward();
  await expect(page.locator(".file-explorer")).toBeVisible();
  await page.getByRole("button", { name: "Images", exact: true }).click();
  await page.getByLabel("Select S001.png", { exact: true }).check();
  await expect(
    page.getByRole("button", { name: "Download selected (1)", exact: true }),
  ).toBeEnabled();
  const pending = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download selected (1)", exact: true })
    .click();
  expect((await pending).suggestedFilename()).toBe("S001.png");
  await page.getByRole("button", { name: "Upload Files", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("05_assets/images");
  await dialog
    .getByLabel("Choose upload files")
    .setInputFiles({
      name: "bad.html",
      mimeType: "text/html",
      buffer: Buffer.from("fixture"),
    });
  await expect(
    page.getByText("Unsupported file type for images", { exact: true }),
  ).toBeVisible();
  await dialog
    .getByLabel("Choose upload files")
    .setInputFiles({
      name: "S001.png",
      mimeType: "image/png",
      buffer: Buffer.from("duplicate"),
    });
  await expect(
    page.getByText(/S001.png already exists. Upload cancelled/),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  // Capture settled UI, after the intentional validation toasts have expired.
  await expect(page.locator("[data-sonner-toast]")).toHaveCount(0, { timeout: 15000 });
  const content = await page
    .locator("#page-content")
    .evaluate((e) => ({
      h: e.clientHeight,
      s: e.scrollHeight,
      overflow: getComputedStyle(e).overflowY,
    }));
  expect(content.overflow).toBe("hidden");
  expect(content.s).toBeLessThanOrEqual(content.h + 1);
  await page.screenshot({ path: "artifacts/dedicated-files/desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Folders", exact: true }).click();
  await expect(page.locator(".mobile-folders-open")).toBeVisible();
  await page.getByRole("button", { name: "Narration", exact: true }).click();
  await expect(page.locator(".mobile-folders-open")).toHaveCount(0);
  await page.waitForTimeout(350);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  await page.screenshot({ path: "artifacts/dedicated-files/mobile.png" });
  await page
    .getByRole("button", { name: "Back to Asset Manager", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Production status" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Upload Files", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("Upload files to OF_R");
  await writeFile(
    "artifacts/dedicated-files/result.json",
    JSON.stringify(
      {
        passed: true,
        checks: [
          "manager has expanded status and no embedded explorer",
          "episode route and refresh/back/forward",
          "selected file download",
          "unsupported type and duplicate cancellation",
          "full-height workspace without page overflow",
          "mobile folder drawer",
          "manager Upload Files opens destination dialog",
        ],
      },
      null,
      2,
    ),
  );
  console.log(
    "PASS: dedicated route, selection/download, upload validation, mobile drawer and manager actions",
  );
} finally {
  await browser.close();
}
