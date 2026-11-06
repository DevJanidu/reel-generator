// Disposable server on 5192 must use artifacts.qa_app:app, never the real provider.
import { chromium, expect as baseExpect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { spawn } from "node:child_process";
const expect = baseExpect.configure({ timeout: 45000 });
const base = "http://127.0.0.1:5192",
  root = process.cwd();
const seed = await new Promise((resolve, reject) => {
  const code = `import json; from services.api import core,creative,main; from tests.fixtures import IDEA,SCRIPT,NARRATION; core.init_db(); main.put_settings({'provider':'manual'}); ep=creative.create_episode(IDEA); core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT); r=creative.approve(ep['id'],NARRATION); creative.run_progress(r['run_id'],'Waiting for model response',0,status='RUNNING'); creative.fail_run(r['run_id'],'TIMEOUT: Worker timeout after 300s'); main.put_settings({'provider':'codex_cli'}); print(json.dumps(dict(episode=ep['id'],failed=r['run_id'])))`;
  const p = spawn("E:/facebook/.venv/Scripts/python.exe", ["-c", code], {
    cwd: root,
    env: {
      ...process.env,
      PYTHONUTF8: "1",
      ODD_DATA_ROOT: root + "/artifacts/preview-data",
      ODD_AI_PROVIDER: "manual",
      ODD_TEST_RUN: "1",
    },
    windowsHide: true,
  });
  let out = "";
  p.stdout.on("data", (d) => (out += d));
  p.stderr.on("data", () => {});
  p.on("exit", (c) =>
    c ? reject(Error("Disposable seed failed")) : resolve(JSON.parse(out)),
  );
});
const token = JSON.parse(
  await readFile("artifacts/preview-data/data/controller-access.json", "utf8"),
).token;
const browser = await chromium.launch({
  executablePath: (await ensureBrowser()).path,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
  errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await mkdir("artifacts/ai-browser", { recursive: true });
try {
  await page.goto(
    base + "/workspace?episode=" + seed.episode + "#controller=" + token,
  );
  const panel = page.getByLabel("Live production activity", { exact: true });
  await expect(panel.getByRole("alert")).toContainText("TIMEOUT");
  await panel.screenshot({ path: "artifacts/ai-browser/failed.png" });
  await page.evaluate(() => {
    window.qaEvents = [];
    window.qaSource = new EventSource("/api/activity/stream");
    window.qaSource.addEventListener("activity", (e) =>
      window.qaEvents.push({
        event: JSON.parse(e.data),
        cursor: e.lastEventId,
      }),
    );
  });
  await page
    .getByRole("button", { name: "Retry / Resume", exact: true })
    .click();
  await expect(panel).toContainText("Attempt 2");
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await expect(panel).toContainText("generating the structured response");
  const rows = await (await fetch(base + "/api/runs")).json();
  const current = rows.find(
    (r) => r.episode_id === seed.episode && r.attempt_number === 2,
  );
  expect(current.status).toBe("RUNNING");
  const runid = current.id;
  const during = await page.evaluate(() => window.qaEvents);
  const received = during.filter(
    (v) =>
      v.event.job_id === runid &&
      v.event.type === "ai.activity" &&
      v.event.message === "Provider is generating the structured response",
  );
  expect(received.length).toBeGreaterThan(0);
  await panel.screenshot({ path: "artifacts/ai-browser/running.png" });
  const cursor = received.at(-1).cursor;
  await page.evaluate(() => window.qaSource.close());
  await page.reload();
  await expect(panel).toContainText("Attempt 2");
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await expect(panel).toContainText("RUNNING");
  await expect(panel).toContainText("SUCCEEDED");
  const ep = await (await fetch(base + "/api/episodes/" + seed.episode)).json();
  expect(ep.data.error).toBeNull();
  expect(ep.data.package).toBeTruthy();
  expect(ep.runs.find((r) => r.id === seed.failed).failure.category).toBe(
    "TIMEOUT",
  );
  // Replay from an actual earlier cursor, using a bounded abort after the first replayed event.
  const abort = new AbortController(),
    response = await fetch(base + "/api/activity/stream", {
      headers: { "Last-Event-ID": cursor },
      signal: abort.signal,
    });
  const reader = response.body.getReader();
  let replay = "";
  for (let i = 0; i < 15 && !replay.includes("event: activity"); i++)
    replay += new TextDecoder().decode((await reader.read()).value);
  abort.abort();
  expect(replay).toContain("event: activity");
  expect(replay).toContain(runid);
  await panel.screenshot({ path: "artifacts/ai-browser/complete.png" });
  await page.getByRole("link", { name: "AI Activity", exact: true }).click();
  await expect(
    page.getByText(new RegExp("Previous attempt 1.*FAILED.*" + seed.failed)),
  ).toBeVisible();
  expect(errors).toEqual([]);
  await writeFile(
    "artifacts/ai-browser/result.json",
    JSON.stringify(
      {
        passed: true,
        episode: seed.episode,
        runid,
        checks: [
          "Timeout visible with diagnosis",
          "Accepted retry clears current error",
          "Provider events received through SSE before process completion",
          "Refresh and lost SSE connection do not restart/cancel attempt",
          "SSE Last-Event-ID replay",
          "Attempt 2 succeeds, Attempt 1 timeout remains historical",
          "Approved narration and final package preserved",
        ],
        errors,
        provider: "Deterministic QA adapter; not a live account",
      },
      null,
      2,
    ),
  );
  console.log(
    "PASS: retry, streaming before completion, refresh, replay and failure history",
  );
} finally {
  await browser.close();
}
