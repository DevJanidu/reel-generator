// Real disposable API + browser UI; static authored fixtures, no live provider calls.
import { chromium, expect as baseExpect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
const expect = baseExpect.configure({ timeout: 45000 });
const root = process.cwd(),
  base = "http://127.0.0.1:5190",
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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }),
  errors = [],
  checks = [];
page.on("pageerror", (e) => errors.push(e.message));
await mkdir("artifacts/storytelling-browser", { recursive: true });
try {
  await page.goto(base + "/ideas#controller=" + token);
  await expect(page.locator(".category-card")).toHaveCount(8);
  expect((await req("/genres")).groups.flatMap((g) => g.genres)).toHaveLength(
    24,
  );
  await page.getByRole("button", { name: /COMEDY & DARK COMEDY/ }).click();
  await page.getByRole("button", { name: "Comedy", exact: true }).click();
  await page
    .getByRole("button", { name: "Story preferences (optional)" })
    .click();
  await page
    .getByRole("combobox", { name: "Human World Connection", exact: true })
    .click();
  await page.getByRole("option", { name: /Pure entertainment/ }).click();
  for (const [label, value] of [
    ["Voice name / ID", "QA measured fixture"],
    ["Measured sample words", "120"],
    ["Measured sample seconds", "60"],
    [
      "Sample file or evidence source",
      "Synthetic QA calibration, not actual ElevenLabs evidence",
    ],
    ["Observation date", "2026-11-06"],
  ])
    await page.getByLabel(label, { exact: true }).fill(value);
  await page.reload();
  await page
    .getByRole("button", { name: "Story preferences (optional)" })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Human World Connection", exact: true }),
  ).toContainText("Pure entertainment");
  await expect(
    page.getByLabel("Measured sample words", { exact: true }),
  ).toHaveValue("120");
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
  expect(session.selection.human_mirror_preference).toBe("pure_entertainment");
  const bundle = await req("/runs/" + batch.run_id + "/request");
  expect(bundle.provenance.skills).toHaveLength(4);
  const payload = JSON.parse(bundle.request.messages[1].content);
  expect(payload.storytelling_plan.timing.measured_voice_wpm).toBe(120);
  const concepts = await fixture(
    "import json,sys; from tests.genre_fixtures import concept_batch; print(json.dumps(concept_batch(json.load(sys.stdin))))",
    payload,
  );
  await page
    .getByLabel("Structured idea response")
    .fill(JSON.stringify(concepts));
  await page
    .getByRole("button", { name: "Validate & Import Five Ideas", exact: true })
    .click();
  await expect(page.locator(".concept-card")).toHaveCount(5);
  await expect(
    page.getByText(/Entertainment-first story/).first(),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/storytelling-browser/ideas.png",
    fullPage: true,
  });
  checks.push(
    "8 groups/24 genres, pure preference + measured calibration refresh persistence, pinned complete-document request, five real validated concepts",
  );
  await page
    .locator(".concept-card")
    .first()
    .getByRole("button", { name: "Select This Story", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Generate your script", exact: true }),
  ).toBeVisible();
  const eid = new URL(page.url()).searchParams.get("episode");
  await expect(page.getByLabel("Full narration", { exact: true })).toHaveCount(
    0,
  );
  await page
    .getByRole("button", { name: "Generate Script", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Generate Script", exact: true }),
  ).toBeEnabled();
  const script = await fixture(
    'import json; from tests.storytelling_samples import script_sample; from tests.storytelling_fixtures import no_mirror; s=script_sample(1); s["human_mirror"]=no_mirror(); print(json.dumps(s))',
  );
  await page.getByLabel("AI JSON response").fill(JSON.stringify(script));
  await page
    .getByRole("button", { name: "Validate & import JSON", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review your script", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("AI JSON response")).toHaveValue("");
  await page.getByLabel("AI JSON response").fill(JSON.stringify(script));
  await page
    .getByRole("button", { name: "Validate & import JSON", exact: true })
    .click();
  await expect(
    page.getByLabel("Full narration", { exact: true }),
  ).toBeEditable();
  const audit = page.getByRole("region", {
    name: "Retention Audit",
    exact: true,
  });
  await expect(
    audit.getByText("Notes match the reviewed narration.", { exact: true }),
  ).toBeVisible();
  await expect(audit.getByText(/10 logic\/continuity warnings/)).toBeVisible();
  await audit
    .getByRole("button", { name: "Logic and continuity checks" })
    .click();
  await expect(
    audit.getByText("Physical rules: warning", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/storytelling-browser/script-audit.png",
    fullPage: true,
  });
  const edited = script.narration + " Pip kept the bow tie.";
  await page.getByLabel("Full narration", { exact: true }).fill(edited);
  await expect(audit.getByText(/Narration has changed/)).toBeVisible();
  await page.getByRole("button", { name: "Save Edits", exact: true }).click();
  await expect
    .poll(async () => (await req("/episodes/" + eid)).data.script.narration)
    .toBe(edited);
  await page.reload();
  await expect(
    page
      .getByRole("region", { name: "Retention Audit" })
      .getByText(/Narration has changed/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "APPROVE SCRIPT & CONTINUE", exact: true })
    .click();
  await expect(
    page.getByLabel("Full narration", { exact: true }),
  ).toBeDisabled();
  expect(
    (await req("/episodes/" + eid)).data.approval.storytelling_context
      .review_matches_approved_wording,
  ).toBe(false);
  checks.push(
    "Real manual script/review imports, complete audit UI, editor freshness before/after save and refresh, one approval locks wording and records stale notes honestly",
  );
  for (const width of [1920, 1440, 1366, 1024, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto(base + "/script?episode=" + eid);
    await expect(
      page.getByRole("region", { name: "Retention Audit" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `artifacts/storytelling-browser/script-${width}.png`,
      fullPage: true,
    });
    if (width === 1440 || width === 390)
      await page.getByRole('region', {name:'Retention Audit'}).screenshot({path:`artifacts/storytelling-browser/audit-${width}.png`});
  }
  checks.push(
    "1920/1440/1366/1024/390 widths: audit reachable and no document horizontal overflow",
  );
  const alternate=await req('/idea-sessions','POST',{category_group_id:'comedy_dark_comedy',primary_genre_id:'comedy'});
  const alternateBatch=await req('/idea-sessions/'+alternate.id+'/batches','POST',{idempotency_key:crypto.randomUUID()});
  const alternateRequest=await req('/runs/'+alternateBatch.run_id+'/request');
  const meaningful=await fixture('import json,sys; from tests.genre_fixtures import concept_batch; from tests.storytelling_samples import script_sample; r=concept_batch(json.load(sys.stdin)); r["ideas"][0]["human_mirror"]=script_sample(1)["human_mirror"]; print(json.dumps(r))',JSON.parse(alternateRequest.request.messages[1].content));
  await req('/runs/'+alternateBatch.run_id+'/import','POST',meaningful);
  await page.setViewportSize({width:1440,height:900});
  await page.goto(base+'/ideas');
  await page.getByRole('combobox',{name:'Saved story sessions'}).selectOption(alternate.id);
  const connection=page.getByRole('button',{name:'Human World Connection',exact:true}).first();
  await connection.click();
  await expect(page.getByText(meaningful.ideas[0].human_mirror.real_world_connection,{exact:true})).toBeVisible();
  await page.locator('.concept-card').first().screenshot({path:'artifacts/storytelling-browser/meaningful-connection.png'});
  checks.push('Same comedy genre accepts both none and subtle modes; meaningful Human World Connection expands in real UI');
  expect(errors).toEqual([]);
  await writeFile(
    "artifacts/storytelling-browser/result.json",
    JSON.stringify(
      {
        passed: true,
        episode: Number(eid),
        checks,
        errors,
        provider: "manual",
        limitation:
          "Static authored fixtures; not live generation or audience performance validation",
      },
      null,
      2,
    ),
  );
  console.log("PASS: " + checks.join("; "));
} finally {
  await browser.close();
}
