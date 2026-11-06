import { chromium, expect } from '@playwright/test';
import { ensureBrowser } from '@remotion/renderer';
import { mkdir, writeFile } from 'node:fs/promises';

// Read-only template; all tested state transitions and mutations are intercepted.
const origin = 'http://127.0.0.1:5174';
const template = await (await fetch(origin + '/api/episodes/2')).json();
const browser = await chromium.launch({ executablePath: (await ensureBrowser()).path });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let current, saved, approved, generated = false;
const draft = { brief: 'A generated fictional story brief for UI verification.', narration: 'She paused at the doorway. The missing key was waiting on the other side.', findings: [] };
function state(script, runs = [], approval = null, status = 'DRAFT') {
  return { ...structuredClone(template), status, runs, data: { ...structuredClone(template.data), script, approval, package: null } };
}
const successful = { id: 'fixture-script', task: 'script', provider: 'codex_cli', status: 'SUCCEEDED' };
await page.route('**/api/episodes/2', r => r.fulfill({ json: current }));
await page.route('**/api/episodes/2/script', r => {
  generated = true;
  current = state(null, [{ ...successful, status: 'RUNNING' }], null, 'SCRIPTING');
  return r.fulfill({ json: { message: 'Fixture generation queued' } });
});
await page.route('**/api/episodes/2/draft', r => {
  saved = r.request().postDataJSON();
  current = state(saved, [successful], null, 'AWAITING_APPROVAL');
  return r.fulfill({ json: current });
});
await page.route('**/api/episodes/2/approve', r => {
  approved = r.request().postDataJSON();
  current = state({ ...draft, ...approved }, [successful], { sha256: 'fixture-approved-hash', revoked: false }, 'PREPARING');
  return r.fulfill({ json: { message: 'Fixture approved' } });
});
async function open() {
  await page.goto(origin + '/script?episode=2');
  await expect(page.getByRole('heading', { name: /Generate your script|Review your script/ })).toBeVisible();
}
try {
  current = state(null);
  await open();
  await expect(page.getByLabel('Full narration', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Save Edits', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate Script', exact: true }).click();
  expect(generated).toBe(true);
  await expect(page.getByText(/Your script is being generated and reviewed/)).toBeVisible();
  await expect(page.getByLabel('Full narration', { exact: true })).toHaveCount(0);
  current = state(null, [{ ...successful, status: 'FAILED' }]);
  await open();
  await expect(page.getByLabel('Full narration', { exact: true })).toHaveCount(0);
  current = state(draft); // An owner-imported draft is not proof of generation.
  await open();
  await expect(page.getByLabel('Full narration', { exact: true })).toHaveCount(0);
  await expect(page.getByText(/An existing imported draft is preserved/)).toBeVisible();
  current = state(draft, [successful, { ...successful, id: 'fixture-review', task: 'review', status: 'RUNNING' }], null, 'SCRIPT_REVIEW');
  await open();
  await expect(page.getByLabel('Full narration', { exact: true })).toBeDisabled();
  current = state(draft, [successful], null, 'AWAITING_APPROVAL');
  await open();
  const narration = page.getByLabel('Full narration', { exact: true });
  await expect(narration).toBeEditable();
  await expect(page.getByLabel('Story brief', { exact: true })).toBeEditable();
  const edited = draft.narration + ' She chose to wait.';
  await narration.fill(edited);
  await page.getByRole('button', { name: 'Save Edits', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save Edits', exact: true })).toBeEnabled();
  expect(saved.narration).toBe(edited);
  await page.getByRole('button', { name: 'APPROVE SCRIPT & CONTINUE', exact: true }).click();
  await expect(narration).toBeDisabled();
  expect(approved.narration).toBe(edited);
  await page.reload();
  await expect(narration).toBeDisabled();
  // Existing approvals remain readable even if their old run evidence is absent.
  current.runs = [];
  await open();
  await expect(narration).toHaveValue(edited);
  await expect(narration).toBeDisabled();
  await mkdir('artifacts/script-editor', { recursive: true });
  await writeFile('artifacts/script-editor/result.json', JSON.stringify({ passed: true, checks: ['empty/running/failed/import-only states hide editor', 'generation action still queues', 'review in progress locks inputs', 'successful generation permits edits', 'save and approval carry edited wording', 'approved script stays read-only after refresh, including legacy approvals'], mutations: 'Intercepted fixtures only; no provider calls or episode writes' }, null, 2));
  console.log('PASS: generated-script editor gating, edits, approval and immutable legacy scripts');
} finally {
  await browser.close();
}
