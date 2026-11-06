# ODD FRAME production integration rehearsal — 2026-11-06

The approved frontend is integrated and tested in a separate worktree. **Production main was not updated**: its 42 modified files, one deletion and 27 untracked source files remain uncommitted. The owner's explicit dirty-worktree stop condition therefore applies, even though those files match the reviewed snapshot.

## Git evidence and recoverability

| Item | Verified value |
|---|---|
| Original and final production main | `af891b2d2a18f2fc103f312899adffd84f526a72` |
| Approved feature HEAD | `8834a9440932f8ef273636c6c70981aa7d1b757d` |
| Reviewed owner-source snapshot | `d445704` |
| Merge base of main / feature | `af891b2` |
| Reconciliation merge | `c65d7ec` (parents main and snapshot) |
| Rehearsal UI merge | `1efeeac` (parents reconciliation and approved feature) |
| Production worktree | `E:/facebook`, branch `main`, dirty and preserved |
| Feature worktree | `E:/facebook-ui-redesign`, branch `feat/shadcn-ui-redesign`, unchanged |
| Rehearsal worktree | `E:/facebook-integration-20261106` |
| Rehearsal branch | `integration/shadcn-reviewed-20261106` |
| Other local branch | `frontend-ui-changes` at `f570621`, already an ancestor of main; no unique work to import |

Both rehearsal operations were real `git merge --no-ff` operations using Git's ort strategy. There were no textual conflicts, no blanket ours/theirs resolutions and no manual directory overlay. Before test-only corrections, the integrated tree matched the approved feature tree exactly. The follow-up commit contains only corrected regression scripts and this evidence/report package; application source remains the approved version.

`artifacts/integration/source-baseline.bundle` stores complete history for main, feature and the older development branch. `git bundle verify` passed. This is a local ignored source-history backup, not a database backup. The original dirty source is additionally recoverable through the exact reviewed snapshot and its hash inventory. No production database copy was necessary because production storage was never migrated or updated by this integration.

## Reconciliation inventory

All **70** changed/deleted/untracked source paths in `SOURCE_SNAPSHOT.json` still match production, including the deletion. Contents also match the committed snapshot after Git CRLF/LF normalization. No additional production source changes were found. The original branch, HEAD, porcelain status and original file SHA-256 checks passed again after verification.

The committed-main-to-feature diff includes the owner's pre-existing backend, prompts, business logic and Studio upgrade; these are not UI-created engine changes. Source separation is:

1. Main-only commits since divergence: none.
2. Dirty-production-only source absent from the reviewed snapshot: none among all 70 reviewed paths.
3. Snapshot `d445704`: all 42 modifications, one deletion and 27 untracked source/config/test/document files.
4. Subsequent feature commits: shadcn components, routing/state/layout, approved neutral theme and semantic status colors, Explorer metadata, interaction corrections, tests and reports.
5. Other development branch: already contained in main's ancestry.

The integration before report/test additions changes 175 paths relative to committed main: **124 added, 50 modified, one removed**. [The exact file/status inventory](evidence/integration-files.json) separates snapshot changes from later UI changes. `apps/dashboard/src/editor.tsx` is the sole removal; it was already deleted by the owner's official-Remotion source upgrade.

Ignored roots were inventoried separately: environment configuration, controller/database files, genuine episodes, virtualenv, dependencies, build/runtime caches and test artifacts. The no-follow inventory recorded **81,583 metadata entries**, skipped reparse aliases and recorded 11 unreadable ignored test-artifact locations. The unrestricted initial Git ignored scan encountered legacy recursive aliases/permission errors; the bounded replacement did not follow them. This is not a claim that inaccessible runtime contents were inspected. The complete ignored-name inventory remains only in `artifacts/integration/ignored-inventory.json`; no ignored secrets or production artifacts were staged.

## Conflict and compatibility review

| File / area | Production vs feature | Resolution and reason | Verification |
|---|---|---|---|
| Existing backend, provider/security/worker code | Dirty production already captured in snapshot | Keep the reviewed snapshot verbatim. No UI-stage changes to these functions. | Original hashes; backend AST/source comparison; 154 tests |
| `services/api/main.py`, `file_catalog.py` | UI adds `file_entries` metadata to episode detail and derives legacy `files` from that catalog | Retain additive read-only metadata, existing file list, link/path protections and all original routes. | 68 identical route signatures; catalog/path/upload/export tests; actual file operations |
| Deleted custom `editor.tsx`; official Studio sources | Owner snapshot replaces old editor with official Remotion workflow | Preserve deletion and official launcher/render project. | Real Studio answered HTTP; owner source edit appeared in final export |
| Frontend main/router/sidebar/state | Old committed UI differs substantially; dirty source contains production actions | Preserve approved feature implementation, including generated-script gating, shared Query keys, routes, scroll containment and all API controls. | Story-to-assets browser workflow; all-page navigation; cancellation/retry/API checks |
| Package manifests/lockfile/Vite/TS | Feature adds official shadcn/Radix/Tailwind/fonts while retaining React, TanStack and Remotion | Retain feature's consistent dependency graph. No unrelated upgrade during rehearsal. | Fresh `npm ci`, `npm ls --all`, both TS checks, Vite build |
| Theme | Earlier task boilerplate says Midnight Gold; owner's later approved UI is neutral | Preserve the reviewed neutral dark appearance with success green/error red/warning yellow. | Current screenshots, route/style checks |
| Database initializer | Owner snapshot adds `idea_sessions` to older committed-main schema | Preserve additive initializer, no production migration. Current production schema already has this table. | Read-only production schema inspection; disposable old-schema upgrade preserved sentinel episode |

No existing route was removed or renamed. The sole UI-stage response-contract addition is public file metadata; upload/download/approval/provider/worker contracts remain unchanged. No database-schema change exists between current dirty production and feature. Production SQLite reports `user_version=0`, `schema_version=13`; this station uses additive initialization rather than a numbered migration framework.

No unresolved merge entries or conflict markers were found. No credentials, databases, episode assets, outputs or local environment values were added. Rollback needs no production data transformation.

## Tests on the integrated application

All commands ran from the rehearsal worktree, using fresh dependencies and disposable stores. Browser scripts used the same source with URLs adapted in ignored runners from 5174 to 5175; the approved feature preview and production service were left running independently. No production credentials or `.env` were copied. No paid/live creative model call was made.

| System | Test performed | Result | Evidence |
|---|---|---|---|
| Dependencies | `npm ci --no-audit --no-fund`; `npm ls --all --json` | PASS | Fresh lockfile install; dependency-tree JSON in ignored integration artifacts. npm noted esbuild postinstall approval metadata, without build failure. |
| Frontend build | `npm run build` (strict dashboard TS + Vite) | PASS | [Build log](evidence/integration-build.log) |
| Remotion types | `npm run typecheck` | PASS | [Typecheck log](evidence/integration-remotion-typecheck.log) |
| Frontend unit tests | `npm run test:ui` | PASS — 12 | [Unit log](evidence/integration-frontend-tests.log) |
| Backend | `python -m pytest -q --basetemp=artifacts/pytest-full-integration --tb=short` with disposable controller root/manual provider | PASS — 154 | [Backend log](evidence/integration-pytest.log); one Starlette/httpx deprecation warning |
| API contracts / schema | Route AST comparison; old-main schema initialized/upgraded in disposable DB with sentinel episode | PASS — 68 routes retained | [Contract/schema results](evidence/integration-contracts-schema.json) |
| Startup | FastAPI 8125 and Vite 5175; actual API connectivity, settings/tools/skills reads | PASS | Separate store `artifacts/preview-data`; no production workers reused |
| Story pipeline | Categories/24 genres, five validated concepts, selection, script/review import, edit/save, approval, package, Flow download | PASS | [Workflow results](evidence/integration-workflow.json); synthetic manual stage responses |
| Script approval | Empty/running/failed/import-only states, successful generation, edit payload, approval/read-only refresh | PASS | [Script results](evidence/integration-script-editor.json); intercepted UI-state fixtures |
| Three-Reel jobs | Three distinct episode workflows, real persisted manual job states and IDs, UI queue/activity | PASS for safe manual workflows | Workflow evidence; native/resource/concurrency regression tests. Three heavy concurrent renders were not started. |
| Provider controls / security | Codex/Claude/manual selectors; invalid settings, capability/Origin rejection; real supported category cancellation/retry and preserved old record | PASS | [API results](evidence/integration-api-checks.json). Manual script handoff cancellation correctly returns 422 because no process is running. |
| Live Codex / Claude generation | Authenticated real model response | NOT TESTED | No account usage was authorized or necessary; mocked-provider regressions/manual contracts do not prove live auth/generation. |
| Asset Manager / Explorer | Expanded checklist, navigation, search/sort, views, preview, multipart audio, matching download bytes, duplicates/invalid types/private paths | PASS | [Asset results](evidence/integration-assets.json), [dedicated route](evidence/integration-dedicated-files.json) |
| Scrolling / responsive | Genuine 80-folder/80-file overflow, both boundaries, keyboard and independent scrollers at 1920x1080, 1440x900, 1366x768, 1024x768, 390px | PASS | [Scroll results](evidence/integration-scroll.json), desktop/mobile screenshots |
| Dashboard / navigation | Every page, refresh, Back/Forward, sidebar persistence/tooltips, error recovery, mobile navigation | PASS | [Route results](evidence/integration-browser.json) |
| Favicon / logo / spacing | SVG/ICO resources, desktop/collapsed/mobile geometry; standalone badge gaps | PASS | [Branding](evidence/integration-branding.json), [spacing](evidence/integration-badge-spacing.json) |
| Accessibility | Axe checks on tested routes and populated Explorer | PASS — zero reported violations | [Axe results](evidence/integration-accessibility.json). This is not exhaustive assistive-technology certification. |
| Official Remotion / export | Real native-isolated editable draft; official Studio HTTP readiness, saved source edit, final render/QC, FFprobe and complete decode | PASS after runtime setup | [Render result](evidence/integration-render.json); 4.923s synthetic engineering Reel, 1080x1920/30fps H.264 + AAC, two-source audio |
| Export UI | Actual preview playback and final download byte equality | PASS | [Export browser result](evidence/integration-export-browser.json), screenshot |
| Analytics | Real stored metrics response, page route and error/loading checks | PASS for existing local functionality | API/browser results. No authenticated Meta integration is implemented/verified; no invented external analytics. |
| Actual production main after merge | Startup/UI/data checks from updated main | BLOCKED | No production merge occurred; main remains dirty at `af891b2`. |

### Failures and corrections observed

- Initial render rehearsal failed closed because the fresh worktree lacked its pinned media runtime. Ran the existing development-only `scripts/setup_media_runtime.py` in the rehearsal worktree, then created a fresh disposable episode. No historical episode was repinned. The second run reached COMPLETE and passed all render/QC assertions. Pillow emitted a deprecation warning on stderr, which PowerShell surfaced as a nonzero wrapper status despite the completed PASS report; an independent complete FFmpeg decode exited successfully afterward.
- The old browser workflow expected the removed pre-generation draft fields and embedded Explorer. Corrected the test to use real script-generation/manual-response/review import contracts and the dedicated route. Asset validation waits for its actual isolated response rather than assuming completion within five seconds.
- The route test incorrectly required absence of all query parameters after the upload-state search addition. It now asserts correct origin/path while preserving supported state parameters; Back/Forward and selected-episode tests still verify their state explicitly.
- The mobile branding test measured two bounds at different points during the Sheet slide animation. It now awaits that animation before comparing settled geometry. Existing transition/centering checks remain.
- An auxiliary API probe initially used POST rather than the existing PUT settings contract, and initially attempted cancellation of an unsupported manual script handoff. Corrected to the actual contract and supported category cancellation; the rejected calls made no settings changes. The full backend suite had already passed.
- The first auxiliary export runner tried to buffer SSE through Playwright route.fetch and encountered canceled download/context errors. Replaced that runner with a real Vite proxy to a read-only API instance (`--lifespan off`, no worker); actual preview playback and byte-identical downloads passed. No application code was changed for these harness issues.

Raw attempt logs remain in ignored `artifacts/integration/`; successful sanitized evidence is linked above. No skipped failure is represented as a pass.

Visual evidence: [desktop Explorer](evidence/integration-files-desktop.png), [mobile Explorer](evidence/integration-files-mobile.png), [actual completed export preview](evidence/integration-export-preview.png). [Dependency/configuration identities](evidence/integration-dependencies.json) and [source/schema audit](evidence/integration-audit.json) preserve the non-secret baseline details.

## Production protection, migration and rollback

The production SQLite database was opened only in read-only/query-only mode for schema inspection. No production API mutation, backup overwrite, schema initializer or sync operation was invoked. No production episode, approved narration, illustration, music, credential, export or cache was copied into the test stores. Shared native runtime setup happened only in the new worktree.

The original uncommitted source is unchanged. The approved feature branch/worktree is unchanged. Production is still usable with its existing version. Rehearsal preview: **http://127.0.0.1:5175**. A second read-only export-check preview at **http://127.0.0.1:5176/exports?episode=1** points only to the disposable completed render store; its API has no lifespan/worker.

Rollback at this point is simply to keep using unchanged production; no production rollback command is needed. Keep the original feature/integration worktrees, bundle and evidence. After any future authorized production update, retain the prior source/build and use an ordinary reviewed revert or clean integration change if necessary; never reset the original dirty worktree or replace newer episode state. No external deployment/push occurred.

## Exact remaining blocker and safest next action

The original running worktree still has the 70 uncommitted source paths. A final merge there could overwrite or conflict with tracked changes and collide with untracked files. Approval of the UI does not override the owner's explicit instruction to stop if dirty production prevents safe final update, or to avoid automatically committing unrelated production changes.

The owner must first authorize and complete a source-only reconciliation/preservation commit for those exact reviewed paths in production (or provide another explicitly reviewed clean target-worktree arrangement). Leave ignored data, credentials and runtime files untouched. Verify the hashes again immediately before that action. This rehearsal already preserves all those contents in `d445704`, but it does not make the original worktree clean.

After production has a clean, reviewed source baseline, rerun an actual three-way merge from its then-current HEAD in a separate worktree. Reassess any new source commits/conflicts, run the critical checks, then use normal Git integration in the clean production worktree. Do not assume the future main commit will be identical to today's rehearsal ancestry. Perform the mandatory actual-main post-merge verification only after that integration; it has not been claimed here.

Known product limitations carried forward: no ZIP/folder downloads or generated-document uploads; selected files download individually. Real provider authentication, external Meta metrics, physical trackpad/touch hardware, subjective story/art quality, music licensing and acoustic alignment were not proven by this rehearsal.

**NOT MERGED — BLOCKED**
