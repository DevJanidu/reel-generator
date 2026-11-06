// Explicit manual fixture integration. Never calls a live model or uses production data.
import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
const root = process.cwd(),
  base = "http://127.0.0.1:5174",
  data = path.join(root, "artifacts/preview-data");
const token = JSON.parse(
  await readFile(path.join(data, "data/controller-access.json"), "utf8"),
).token;
const req = async (p, method = "GET", body) => {
  const r = await fetch(base + "/api" + p, {
    method,
    headers: { "content-type": "application/json", "x-odd-controller": token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const value = await r.json();
  if (!r.ok) throw Error(JSON.stringify(value));
  return value;
};
const fixture = (code, payload = {}) =>
  new Promise((resolve, reject) => {
    const p = spawn("E:/facebook/.venv/Scripts/python.exe", ["-c", code], {
      cwd: root,
      env: {
        ...process.env,
        PYTHONUTF8: "1",
        ODD_DATA_ROOT: data,
        ODD_AI_PROVIDER: "manual",
      },
      windowsHide: true,
    });
    let out = "";
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", () => {});
    p.on("exit", (c) =>
      c ? reject(Error("Fixture failed")) : resolve(JSON.parse(out)),
    );
    p.stdin.end(JSON.stringify(payload));
  });
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const checks = [];
await mkdir("artifacts/workflow-qa", { recursive: true });
try {
  await page.goto(base + "/ideas#controller=" + token);
  await expect(page.locator(".category-card")).toHaveCount(8);
  const taxonomy = await req("/genres");
  expect(taxonomy.groups.flatMap((g) => g.genres)).toHaveLength(24);
  await page.getByRole("button", { name: /COMEDY & DARK COMEDY/ }).click();
  await page.getByRole("button", { name: "Comedy", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate 5 Story Ideas", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Generate 5 Story Ideas", exact: true }),
  ).toBeFocused();
  await page
    .getByRole("button", { name: "Generate 5 Story Ideas", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirm & Generate", exact: true })
    .click();
  await expect(
    page.getByText("Manual handoff ready", { exact: true }),
  ).toBeVisible();
  const state = JSON.parse(
    await page.evaluate(() =>
      localStorage.getItem("odd-frame-genre-selection-v2"),
    ),
  );
  const session = await req("/idea-sessions/" + state.session),
    batch = session.batches.at(-1);
  const bundle = await req("/runs/" + batch.run_id + "/request");
  expect(bundle.provenance.skills).toHaveLength(4);
  const concepts = await fixture(
    "import json,sys; from tests.genre_fixtures import concept_batch; print(json.dumps(concept_batch(json.load(sys.stdin))))",
    JSON.parse(bundle.request.messages[1].content),
  );
  await page
    .getByLabel("Structured idea response")
    .fill(JSON.stringify(concepts));
  await page
    .getByRole("button", { name: "Validate & Import Five Ideas", exact: true })
    .click();
  await expect(page.locator(".concept-card")).toHaveCount(5, {
    timeout: 15000,
  });
  checks.push(
    "8 groups, 24 genres, official Dialog focus/Escape, five validated manual concepts",
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "artifacts/workflow-qa/ideas.png",
    fullPage: true,
  });
  await page
    .locator(".concept-card")
    .first()
    .getByRole("button", { name: "Select This Story", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Generate your script",
      exact: true,
    }),
  ).toBeVisible({ timeout: 30000 });
  const selected = new URL(page.url()).searchParams.get("episode");
  expect(selected).toBeTruthy();
  await page.reload();
  await expect(page.getByLabel("Active Reel", { exact: true })).toHaveValue(
    selected,
  );
  checks.push("Story selection, episode URL and refresh persistence");
  const source = await fixture(
    "import json; from tests.fixtures import SCRIPT,NARRATION,package; print(json.dumps(dict(script=SCRIPT,narration=NARRATION,package=package())))",
  );
  await expect(page.getByLabel("Full narration", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Generate Script", exact: true }).click();
  await page.getByLabel("AI JSON response").fill(JSON.stringify(source.script));
  await page.getByRole("button", { name: "Validate & import JSON", exact: true }).click();
  // Import the subsequent retention review through the same real API/UI contract.
  await expect(page.getByRole("heading", { name: "Review your script", exact: true })).toBeVisible();
  await page.getByLabel("AI JSON response").fill(JSON.stringify(source.script));
  await page.getByRole("button", { name: "Validate & import JSON", exact: true }).click();
  await expect(page.getByLabel("Full narration", { exact: true })).toBeEditable();
  await page
    .getByLabel("Story brief", { exact: true })
    .fill(source.script.brief);
  await page
    .getByLabel("Full narration", { exact: true })
    .fill(source.narration);
  await page
    .getByRole("button", { name: "Save Edits", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "APPROVE SCRIPT & CONTINUE" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "APPROVE SCRIPT & CONTINUE" }).click();
  await expect(
    page.getByLabel("Full narration", { exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel("AI JSON response")
    .fill(JSON.stringify(source.package));
  await page
    .getByRole("button", { name: "Validate & import JSON", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Google Flow Prompts", exact: true })
    .and(page.locator("a"))
    .click();
  await expect(
    page
      .getByRole("link", { name: "Download Flow JSON", exact: true })
      .and(page.locator("a")),
  ).toBeVisible();
  const link = await page
    .getByRole("link", { name: "Download Flow JSON", exact: true })
    .and(page.locator("a"))
    .getAttribute("href");
  const flow = await fetch(base + link).then((r) => r.json());
  expect(flow.jobs).toHaveLength(3);
  expect(flow.jobs.every((j) => j.type === "image")).toBe(true);
  checks.push(
    "Draft save, single approval, immutable wording, complete package import and Flow download",
  );
  await page
    .getByRole("link", { name: "Asset Manager", exact: true })
    .and(page.locator("a"))
    .click();
  await page
    .getByRole("button", { name: "Refresh Assets", exact: true })
    .click();
  await expect(page.getByText(/S001: need exactly one/)).toBeVisible({ timeout: 120000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "artifacts/workflow-qa/assets.png",
    fullPage: true,
  });
  checks.push("Real asset validation and missing-asset feedback");
  await page.getByRole("button", { name: "Open File Explorer", exact: true }).click();
  await page.getByRole("button", { name: "Images", exact: true }).click();
  await page.getByLabel("Import images", { exact: true }).setInputFiles({
    name: "S001.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jA1sAAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await expect(
    page.getByRole("button", { name: "Preview S001.png", exact: true }),
  ).toBeVisible();
  checks.push("Real multipart upload into disposable episode");

  await page
    .getByRole("link", { name: "AI Activity", exact: true })
    .and(page.locator("a"))
    .click();
  await expect(page.getByText("Saved activity", { exact: true })).toBeVisible();
  await expect(page.locator(".activity-job")).not.toHaveCount(0);
  checks.push("Backend job states and generated outputs");
  await page
    .getByRole("link", { name: "Settings", exact: true })
    .and(page.locator("a"))
    .click();
  await page.getByLabel("AI provider", { exact: true }).selectOption("manual");
  await page
    .getByRole("button", { name: "Save settings", exact: true })
    .click();
  expect((await req("/settings")).provider).toBe("manual");
  checks.push("Authorized settings save to disposable database");
  const idea = await fixture(
    "import json; from tests.fixtures import IDEA; print(json.dumps(IDEA))",
  );
  const peers = [];
  for (let i = 0; i < 2; i++) {
    const ep = await req("/episodes", "POST", {
      ...idea,
      title: "Disposable parallel workflow " + i,
    });
    await req("/episodes/" + ep.id + "/script", "POST");
    peers.push(ep.id);
  }
  const recorded = await req("/activity");
  expect(
    peers.every((id) =>
      recorded.some(
        (j) => j.episode_id === id && j.status === "AWAITING_MANUAL",
      ),
    ),
  ).toBe(true);
  await page
    .getByRole("link", { name: "Production Queue", exact: true })
    .and(page.locator("a"))
    .click();
  await expect(
    page.getByText("AWAITING MANUAL", { exact: true }).first(),
  ).toBeVisible();
  checks.push(
    "Independent persisted job states across three disposable Reel workflows; no live workers",
  );

  expect(errors).toEqual([]);
  const report = {
    passed: true,
    checks,
    errors,
    episode: Number(selected),
    limitations: [
      "Manual synthetic import covers generation contracts; no paid/live model call",
      "Actual render and native enforcement were not exercised by this browser script",
    ],
  };
  await writeFile(
    "artifacts/workflow-qa/result.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
} catch (e) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "artifacts/workflow-qa/failure.png",
    fullPage: true,
  });
  throw e;
} finally {
  await browser.close();
}
