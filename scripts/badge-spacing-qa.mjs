import { chromium, expect } from '@playwright/test';
import { ensureBrowser } from '@remotion/renderer';
import { mkdir, writeFile } from 'node:fs/promises';
const browser = await chromium.launch({ executablePath: (await ensureBrowser()).path });
const page = await browser.newPage();
await mkdir('artifacts/badge-spacing', { recursive: true });
const checked = [];
try {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ['assets', 'workspace']) {
      await page.goto(`http://127.0.0.1:5174/${route}?episode=2`);
      await expect(page.locator('.panel > [data-slot="badge"]').first()).toBeVisible();
      const badges = await page.locator('.panel > [data-slot="badge"]').evaluateAll(nodes => nodes.map(e => {
        const r = e.getBoundingClientRect(), next = e.nextElementSibling?.getBoundingClientRect(), previous = e.previousElementSibling?.getBoundingClientRect();
        return { text: e.textContent, after: next ? next.top - r.bottom : null, before: previous ? r.top - previous.bottom : null };
      }));
      for (const badge of badges) {
        if (badge.after !== null) expect(badge.after).toBeGreaterThanOrEqual(15);
        if (badge.before !== null) expect(badge.before).toBeGreaterThanOrEqual(11);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      checked.push({ width, route, badges });
      if (route === 'assets') {
        const panel = page.locator('.panel').filter({ has: page.getByRole('heading', { name: 'Asset validation', exact: true }) });
        await panel.screenshot({ path: `artifacts/badge-spacing/validation-${width}.png` });
      }
    }
  }
  await writeFile('artifacts/badge-spacing/result.json', JSON.stringify({ passed: true, checked }, null, 2));
  console.log('PASS: standalone badge spacing on Asset Manager/Workspace at desktop/mobile; no horizontal page overflow');
} finally { await browser.close(); }
