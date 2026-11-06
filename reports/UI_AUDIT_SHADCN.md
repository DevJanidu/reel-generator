# ODD FRAME UI audit

Read-only audit completed 2026-11-06 before branch creation. Original main HEAD: af891b2d2a18f2fc103f312899adffd84f526a72. Audit covers current owner source, including uncommitted upgrades, not just committed HEAD. No production mutation, provider call or render was performed.

## Architecture
Existing npm workspaces: dashboard Vite 8 / React 19 / strict TypeScript 5.9 / Tailwind 4; TanStack Query 5 and Router 1; lucide icons. No shadcn configuration or components initially. Main dashboard is a 2,646-line component; Ideas, Activity, Exports, paging and official Studio are separate. Three router entries (/ , /help, /episodes/$episodeId/editor); all main pages use local state. API contracts live in services/api/main.py with typed Pydantic creative contracts; no schema changes needed. Root typecheck targets Remotion only, so dashboard must be checked separately.

## Severity-ranked findings
|Severity|Finding|Code|Recommendation|
|---|---|---|---|
|High|Navigation and selected episode lost on refresh; browser back/forward cannot follow pages|main.tsx:121; router.tsx|Router-owned page URLs and episode search parameter|
|High|Server state mirrored in local state; overlapping 5s and 1.5s polls; stale responses can cross episode selection|main.tsx:183-245|Query observers, shared keys, cancellation and mutation invalidation|
|High|8-13px interface text and mobile icon-only navigation without explanatory tooltips|style.css:17,148,930|16px body, semantic typography and official Sidebar|
|High|Activity drawer lacks modal focus handling|activity.tsx:34|Official Sheet with focus return and Escape|
|Medium|Fallback scene count 18 can imply measured asset requirements when package unavailable|main.tsx:403|Unknown state until package confirmed|
|Medium|Duplicate untyped API helpers; JSON parse assumptions; missing abort signals|main.tsx:56; api.ts|One generic service with normalized errors and AbortSignal|
|Medium|Oversized decorative home hero; repeated skills/provider/production explanations|main.tsx:891; style.css:277|Compact action-led dashboard and details disclosure|
|Medium|No dedicated queue, health or A-Z guide navigation|main.tsx:43; router.tsx|Expose existing status/jobs/tools and searchable help|
|Medium|Loading and failure can look like empty data; some initial fetch failures unhandled|main.tsx:246; studio.tsx:73|Skeletons, explicit retry/error states|
|Medium|Exports deletion confirmation inline; QC link points at common report rather than proven per-version report|exports.tsx|AlertDialog; describe current report honestly|
|Low|Hardcoded colors and global element styles compete with newer Ideas styles|style.css; ideas.css|Semantic tokens and scoped legacy layout|

## Screen review
All rows include source-level functionality review; live keyboard, timings and current browser behavior remain unverified until automated preview checks. Screenshots from earlier runs are historical, not new execution evidence.

|Screen / current route|Findings and preserved behavior|Recommended design|
|---|---|---|
|Home /|Real status counts and recent episodes; large hero; seven small metrics; missing first-load distinction|Compact metrics, recent production, approvals/assets and next action|
|Master Prompt / local page|Real /api/master read; long small preformatted text|Readable document surface and copy/download|
|Genre/Ideas / local page|Eight groups/24 genres, persisted selection, five concepts, batch history, manual handoff; native dialog focus code already exists|Preserve logic, use shadcn Dialog and category cards|
|Script Studio / local page|Real draft/save/generate/approval; approved text disabled; global busy|Readable editor, clear immutable state, explicit approval|
|Episode Workspace / local page|Pipeline and files/history/provenance exist; repeated technical panels|Next action first, supporting evidence in disclosure|
|Flow / local page|Image-only prompt downloads and scene details exist|Scene list and export actions; do not imply generated images|
|Assets / local page|Real file upload, refresh, rights confirmation and missing assets; no byte progress|Clear asset roles/status; honest upload busy indicator|
|AI Activity / global drawer|SSE replay, real elapsed and provider, retry/cancel; no fake percentage|Accessible Sheet plus dedicated activity route|
|Production Queue / absent|Jobs available through status API and activity; no capacity overview|Independent job rows and separate AI/render slots; no concurrency backend change|
|Remotion / Edit Studio local page|Real readiness/error, launch and source-edits preservation exist|One prominent launcher; advanced rebuild/style actions disclosed|
|Exports / local page|Real filenames/downloads, pagination and two-step deletion; current QC link|Readable rows, safe AlertDialog; preserve versions|
|Analytics / local page|Owner-entered actual metrics; no fabricated retention|Clear manual-data labeling and empty state|
|Settings / local page|Real provider/model/concurrency, credential controls, live provider diagnostics|Grouped sections, clear diagnostic usage and authorization|
|How to Use /help|Progress guide only; no searchable full A-Z guide|Searchable Accordion, workflow shortcuts|
|System Health / absent|Tools/skills/isolation/provider state exist|Read-only health route, no invented isolation claims|

## Evidence and baseline checks
Dashboard tsc passed in the original read-only audit. Historical screenshot review: artifacts/dropdown-ui/episode-desktop.png shows small labels and unused space; provider-mobile.png shows readable select options but cramped permanent icon rail. Historical artifacts/ui-smoke/latest.json reports PASS, but is not fresh validation. Native/browser hosts were unavailable in the initial audit. Performance profiling and screen-reader testing unverified. Existing good components: genre selection semantics/focus restoration, streamed allowlisted job metadata, immutable script controls, official Studio, real download/upload contracts, searchable paging.

## Source inventory
All 42 modifications, one deletion and 27 untracked paths are listed below and SHA-256 values are in SOURCE_SNAPSHOT.json. Each file was read for inventory and secret-pattern screening. Prompt Markdown is executable creative configuration, not disposable documentation. Worker, provider, Remotion and prompt changes are owner baseline changes, not redesign changes. Preserve byte-for-byte.

|Status|Path|Classification|
|---|---|---|
| M|AI_PROVIDERS.md|Tests and documentation|
| M|README.md|Tests and documentation|
| M|WORKFLOW.md|Tests and documentation|
| M|apps/dashboard/src/activity.tsx|Intended application source|
| M|apps/dashboard/src/api.ts|Intended application source|
| D|apps/dashboard/src/editor.tsx|Intended application source|
| M|apps/dashboard/src/main.tsx|Intended application source|
| M|apps/dashboard/src/router.tsx|Intended application source|
| M|brand/EDITING_PROFILES.json|Required configuration and dependencies|
| M|brand/ODD_FRAME_RULES.json|Required configuration and dependencies|
| M|brand/SKILLS_MANIFEST.json|Required configuration and dependencies|
| M|package-lock.json|Required configuration and dependencies|
| M|prompts/00_MASTER_PROMPT.md|Required configuration and dependencies|
| M|prompts/01_IDEA_GENERATION.md|Required configuration and dependencies|
| M|prompts/02_SCRIPT_WRITING.md|Required configuration and dependencies|
| M|prompts/03_SCRIPT_REVIEW.md|Required configuration and dependencies|
| M|prompts/04_CHARACTER_BIBLE.md|Required configuration and dependencies|
| M|prompts/05_STORYBOARD.md|Required configuration and dependencies|
| M|prompts/08_REMOTION_EDIT.md|Required configuration and dependencies|
| M|scripts/cli_worker.py|Intended application source|
| M|scripts/production_worker.py|Intended application source|
| M|scripts/render_smoke.py|Tests and documentation|
| M|scripts/ui-smoke.mjs|Tests and documentation|
| M|scripts/write_stage_prompts.py|Intended application source|
| M|services/api/activity.py|Intended application source|
| M|services/api/core.py|Intended application source|
| M|services/api/creative.py|Intended application source|
| M|services/api/editor.py|Intended application source|
| M|services/api/main.py|Intended application source|
| M|services/api/media.py|Intended application source|
| M|services/api/models.py|Intended application source|
| M|services/api/providers.py|Intended application source|
| M|services/api/skills.py|Intended application source|
| M|services/api/snapshots.py|Intended application source|
| M|services/api/styles.py|Intended application source|
| M|services/api/worker.py|Intended application source|
| M|tests/test_editor_activity.py|Tests and documentation|
| M|tests/test_style.py|Tests and documentation|
| M|video/remotion/package.json|Required configuration and dependencies|
| M|video/remotion/src/composition.tsx|Intended application source|
| M|video/remotion/src/index.tsx|Intended application source|
| M|workflows/REEL-CREATE.md|Tests and documentation|
| M|workflows/REEL-EDIT.md|Tests and documentation|
|??|EDITING_TRANSITIONS.md|Tests and documentation|
|??|REMOTION_STUDIO.md|Tests and documentation|
|??|STORY_IDEAS.md|Tests and documentation|
|??|apps/dashboard/src/exports.tsx|Intended application source|
|??|apps/dashboard/src/ideas.css|Intended application source|
|??|apps/dashboard/src/ideas.tsx|Intended application source|
|??|apps/dashboard/src/paging.css|Intended application source|
|??|apps/dashboard/src/paging.tsx|Intended application source|
|??|apps/dashboard/src/studio.tsx|Intended application source|
|??|brand/STORY_GENRES.json|Required configuration and dependencies|
|??|scripts/apply_transition_decisions.py|Intended application source|
|??|scripts/genre-ui-smoke.mjs|Tests and documentation|
|??|scripts/transitions_verify.py|Tests and documentation|
|??|scripts/ui_pages_seed.py|Tests and documentation|
|??|services/api/genres.py|Intended application source|
|??|services/api/idea_models.py|Intended application source|
|??|services/api/story_ideas.py|Intended application source|
|??|services/api/studio.py|Intended application source|
|??|tests/genre_fixtures.py|Tests and documentation|
|??|tests/test_credentials.py|Tests and documentation|
|??|tests/test_exports_delete.py|Tests and documentation|
|??|tests/test_genre_ideas.py|Tests and documentation|
|??|tests/test_studio.py|Tests and documentation|
|??|tests/test_transitions.py|Tests and documentation|
|??|video/remotion/preview-studio.mjs|Intended application source|
|??|video/remotion/render-studio.mjs|Intended application source|
|??|video/remotion/src/library.tsx|Intended application source|

Generated/runtime files: none in these 70 paths. Secrets/private configuration: none detected in the selected paths; .env, auth stores, data, episodes, exports, caches and node_modules excluded. Uncertain files: none excluded; scripts/ui_pages_seed.py and transition helper are retained as development utilities and not executed against production. Automated pattern screening is limited and does not constitute a credential audit. Existing tracked source uploads remain tracked and unchanged.

