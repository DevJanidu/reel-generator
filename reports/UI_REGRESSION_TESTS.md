# UI regression verification

Executed 2026-11-06 in E:/facebook-ui-redesign. All mutations used disposable data. No paid or live creative provider calls were made.

|Check|Result|Evidence / scope|
|---|---|---|
|Dashboard TypeScript and Vite build|PASS|npm run build; strict dashboard tsc runs before Vite|
|Remotion TypeScript|PASS|npm run typecheck|
|Frontend unit tests|12 PASS|npm run test:ui; transport, status semantics and folder isolation/natural sorting/size checks|
|Complete existing backend suite|151 PASS|python -m pytest -q --basetemp=artifacts/snapshot-pytest-2 --tb=short; 770.84 seconds|
|Focused backend regressions|38 PASS|editor/activity, genre ideas and export deletion tests|
|All page routes and responsive layout|PASS|scripts/redesign-qa.mjs; 1440px desktop and 390px mobile; no page overflow|
|Navigation persistence|PASS|refresh, episode search parameter, back/forward, collapsed preference and tooltips|
|Keyboard dialogs|PASS|genre focus/Escape restoration, Activity Sheet Escape, mobile navigation Sheet|
|Manual complete workflow|PASS|scripts/redesign-workflow-qa.mjs; real disposable API integration and synthetic structured creative fixtures|
|Independent workflow states|PASS|three disposable Reel workflows with real persisted manual job states; not three live automatic workers|
|Asset upload and validation|PASS|actual multipart still-image upload, actual missing-asset errors; no fabricated progress|
|Authorized settings|PASS|manual provider saved to disposable database|
|Request error and retry|PASS|deliberate browser-local 503 fixture, explicit retry restores actual backend data|
|Cross-origin protection|PASS|foreign Origin mutation rejected with HTTP 403 through preview proxy|
|User visual corrections|PASS|visible Reel text on transparent links, neutral white primary buttons, sidebar gap >=6px, neutral/open Help accordion; green success/red error/yellow warning semantics|
|Accessibility|PASS|axe WCAG 2 A/AA + 2.1 AA; zero violations on 14 checked routes including populated episode pages|
|Dependency audit|PASS|npm audit: zero vulnerabilities|
|Original source preservation|PASS|scripts/verify-redesign-snapshot.py compares main HEAD/status and all 70 original source states/hashes|
|Engine scope|PASS|no services/brand/prompts/video changes after d445704|

## Workflow coverage

The browser selects a category and genre, confirms a five-idea request, imports five schema-validated manual concepts, selects a story, restores its episode after refresh, saves a draft, approves once, checks disabled approved narration, imports a preparation package, downloads genuine image-only Flow JSON, refreshes assets, uploads a still, views activity, saves authorized settings, and displays independently persisted jobs.

The backend suite includes actual official Remotion Studio start/readiness/reuse/stop, source-policy and immutability checks, export deletion, path boundaries and schema checks. This does not establish a new native MXC smoke test or a new final production render. No production episodes were used.

## Limits and unverified checks

- Live Codex/Claude/API generation, three simultaneous isolated automatic workers, full native sandbox smoke probes and a fresh end-to-end final render were not executed in this redesign task.
- Existing export download/deletion contracts have backend tests. The redesigned video preview control was built but playback against a newly rendered export remains unverified.
- Listening, acoustic sync, licensing, story quality and real analytics were not inferred from machine tests.
- Axe and keyboard automation do not replace a human screen-reader/browser review. Tests used Chromium; other browser engines and actual touch hardware are unverified.
- Root typecheck only covers Remotion; dashboard build separately covers dashboard TypeScript.
- Initial pytest attempt failed because artifacts did not exist. The directory was created and the complete corrected run passed. The only remaining test warning is Starlette's httpx TestClient deprecation.

## Reproduction

Start the disposable preview with `npm run ui:preview`, then run:

```
npm run build
npm run typecheck
npm run test:ui
node scripts/redesign-workflow-qa.mjs
node scripts/redesign-qa.mjs
node scripts/redesign-accessibility.mjs
E:/facebook/.venv/Scripts/python.exe scripts/verify-redesign-snapshot.py
npm audit
```

Browser scripts read the disposable controller capability locally and never print its value. Full test outputs and screenshots remain under ignored artifacts; selected non-sensitive evidence is retained in reports/evidence.


Ideas layout follow-up: `node scripts/ideas-layout-qa.mjs` passed at 1920/1440/768/390px; all eight cards have 18px corners and contained children, selection works and no page overflow occurs. Vite/TypeScript build passed. Evidence: reports/evidence/ideas-layout-results.json.


## Asset explorer follow-up

- `node scripts/asset-explorer-qa.mjs`: PASS against real disposable episode metadata. Tests separate/empty/nested folders, search and sorting, grid/list switching, text/audio previews, successful multipart upload, byte-identical download, cancellation of remove confirmation, private-folder exclusion and desktop/390px layout. Zero axe WCAG A/AA violations on the populated explorer.
- `pytest tests/test_file_catalog.py`: 3 PASS (nested/empty folders, private/temp exclusions, hard-link rejection).
- Existing API/path-safety and export regressions: 5 PASS after the read-only metadata extension.
- Dashboard build/TypeScript and 12 frontend unit tests PASS. No live providers or production mutations were used.
- Source preservation verification still compares all original main hashes/status; the reviewed read-only catalog/detail metadata is now the only permitted backend exception. No worker, creative, database-schema or renderer changes.


Hover/spacing follow-up: `node scripts/layout-polish-qa.mjs` PASS. Every rendered Home Reel/next-action row was hovered and checked for neutral background/readable foreground. Expanded/collapsed/mobile logo bounds pass, header gap is at least 12px, batch label/control gaps at least 8px, production-history search spacing at least 12px, authorization alert top/bottom separation at least 16px. Short-page alignment and mobile overflow pass. Axe on the unauthenticated alert page and all checked routes reports zero violations. Dashboard build, 12 unit tests and the general desktop/mobile route regression pass. No backend or production-state changes.
