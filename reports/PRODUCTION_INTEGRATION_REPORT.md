# ODD FRAME — completed production merge

The source-preservation blocker is resolved. The approved UI is merged into actual `main` at `E:/facebook` and runs through the normal station startup at **http://127.0.0.1:8123**. This is not a preview worktree. Actual-main build, API, browser and disposable native-render checks passed. Live model/external-service checks remain unverified; the Windows cleanup limitation below is disclosed.

## Git evidence

| Stage | Commit |
|---|---|
| Original production HEAD | `af891b2d2a18f2fc103f312899adffd84f526a72` |
| Approved feature | `8834a9440932f8ef273636c6c70981aa7d1b757d` |
| Previous integration | `2dd50e5c093f3689ff7cbd9c677d74c41eca256f` |
| Authorized preservation on main | `1852335e623d8676591073e4841c5d3f358cb9f6` |
| Source reconciliation merge | `ef6e9b0` |
| Fresh UI integration merge | `873633c` |
| Final tested candidate | `6f6d2d3ff8b6c5008f30f670011d8dde332f87f2` |
| Actual main application merge | `b23c2028fc5908b02f130b2ffccdccee76362543` |

The final main HEAD also contains the documentation/evidence follow-up carrying this report. Its exact resulting ref is recorded after that commit in the local [final ref manifest](../artifacts/production-merge/final-head.json); the tested application commit above is unchanged by the report-only follow-up.

All worktrees remain: production `E:/facebook` (`main`); approved feature `E:/facebook-ui-redesign` (`feat/shadcn-ui-redesign`); earlier rehearsal `E:/facebook-integration-20261106` (`integration/shadcn-reviewed-20261106`); fresh rehearsal `E:/facebook-final-integration-20261106` (`integration/shadcn-final-20261106`). Nothing was pushed or deployed externally, rebased, reset, stashed, cleaned, or deleted.

## Source preservation and reconciliation

Reinspected current status, commits, branches, worktrees, process ownership and the earlier report. The **42 modified, one deleted and 27 untracked source paths** still matched all original snapshot hashes. Classification: **36 application-source files, 13 required configuration/dependency files, 21 test/documentation files**. No uncertain path remained. Ignored credentials/environment, databases, episodes, media, exports, dependencies and caches were reviewed separately and excluded.

Staged only the 70 explicit manifest paths, including the intentional deletion and every new source file. Compared each staged blob with `d445704`, inspected the complete staged list/diff, checked credential patterns and ran `git -c core.whitespace=cr-at-eol diff --cached --check`. Git's normal CRLF normalization was accounted for. Independent source reads confirmed stability; production had no active AI/render jobs. Commit `1852335` preserved the exact reviewed source and left main clean. [Preservation evidence](evidence/production-preservation.json).

Created a fresh rehearsal from preserved main. An actual `--no-ff` merge of the equivalent snapshot added only the two audit/snapshot reports: all 70 source blobs were identical. The resulting tree exactly matched `d445704`. Merging the previous integration then produced the approved UI tree, exactly matching `2dd50e5`. This reconciles ancestry without repeating source edits or overwriting newer work.

There were **no textual conflicts** and no blanket ours/theirs decisions. Candidate `6f6d2d3` adds an actual-main read-only browser test and correct asynchronous workflow-test waits; no application/backend/engine implementation changed during this final rehearsal. After verification and another clean/no-active-jobs/data check, a normal `--no-ff` merge on actual main created `b23c202`, matching the candidate tree.

The [exact file inventory](evidence/production-merge-files.json) separates preservation, UI integration and complete original-to-merged changes. Before this report follow-up, the application merge changed 200 paths from original main; preservation alone covered 70. The custom editor deletion was already intended owner work and retains the official Remotion Studio replacement.

## Compatibility review

- Latest production providers, security, workers, business logic, concurrency limits, pinned inputs/music and approved-wording rules remain. All **68** reviewed API route signatures were retained.
- The sole UI-stage backend addition is reviewed read-only file metadata in episode detail; legacy `files` remains. Upload/download, authorization, path/link validation and approval contracts were not weakened.
- The approved shadcn shell, owner-selected neutral dark theme, semantic status colors, OF favicon, responsive/scroll behavior, Query/router state, Script Studio gating, Asset Manager and dedicated Explorer are preserved.
- npm used the approved lockfile without unrelated upgrades. Both candidate and actual-main installs, builds and TypeScript checks passed. The production HTTP index was compared byte-for-byte with the main build.
- No schema change exists relative to the previously running production source. Existing additive initialization was retained; no destructive production migration was run. Disposable schema tests preserved an existing sentinel row.
- No database, private environment, credentials, episode media or final video was committed. New evidence contains summaries/metadata; raw logs and media generated for these final checks remain ignored. Previously reviewed test-output documentation from the integration branch remains in its history.

## Verification

| System | Actual test | Result | Evidence |
|---|---|---|---|
| Preservation | Exact staged paths/blobs, secrets/whitespace, source stability, no active jobs | PASS | [Preservation](evidence/production-preservation.json) |
| Final candidate backend | Full pytest suite with disposable controller/storage | **154 passed**, one existing Starlette/httpx warning | [Candidate results](evidence/final-candidate-results.json); final rehearsal `artifacts/final-merge/backend-tests.log` |
| Candidate frontend | Clean npm install, strict dashboard TS/Vite, 12 unit tests, Remotion types | PASS | Final rehearsal `artifacts/final-merge/` outputs |
| API/schema | 68-route comparison, disposable schema initialization, controller/Origin rejection, invalid settings, supported cancellation/retry | PASS | Candidate results, API/contract checks |
| Complete story workflow | Eight groups/24 genres, five ideas, selection, script/review imports, editing, approval, package/Flow, assets/settings | PASS with synthetic manual responses | Candidate results, story checks |
| Queue/Activity | Three independent disposable Reel states, unique IDs and isolated files, persisted jobs, backend concurrency tests | PASS for safe manual/mocked cases | Candidate results; no three heavy production renders |
| Explorer/assets | Expanded checklist, route, folders/search/sort/views/preview, real uploads and matching downloads, duplicates/invalid/private paths | PASS | Candidate results, assets/files checks |
| Scroll/responsive | Real 80-folder/80-file overflow and boundaries, keyboard, 1920x1080 / 1440x900 / 1366x768 / 1024x768 / 390px | PASS | Candidate results, scroll checks |
| Navigation/accessibility | All routes, Back/Forward, sidebar/tooltips/mobile drawer/favicon/spacing, axe | PASS; zero reported axe violations | Candidate results |
| Candidate native render | Official Studio, retained source edit, final render/QC/decode | PASS after orphan helper cleanup | Candidate render result in final rehearsal artifacts; limitation below |
| **Actual main build** | `npm ci --no-audit --no-fund`, `npm run build`, `npm run typecheck` | **PASS** | [Main verification](evidence/main-verification.json); local build/typecheck outputs |
| **Actual main unit tests** | `npm run test:ui` | **12 passed** | Local `artifacts/production-merge/unit-tests.log` |
| **Actual main backend/API** | Catalog/export/HTTP import/path-safety tests with disposable storage | **8 passed**, one existing warning | Local `artifacts/production-merge/api-tests.log` |
| **Actual production startup** | Normal `scripts/start.ps1 -NoBrowser`, main source/store, port 8123 | **PASS** | Local startup logs; FastAPI startup complete |
| **Actual production UI** | `node scripts/production-merge-qa.mjs` against 8123; genuine completed Reel; sidebar, selection, Explorer, Queue/Activity/Studio/Exports/Analytics/Health, mobile | **PASS**, no JavaScript errors | [Main browser results](evidence/main-browser-results.json) |
| **Existing genuine export** | Actual preview playback and download bytes compared with original MP4 | **PASS** | Main browser results; screenshots remain local in `artifacts/production-merge/` |
| **Actual main Studio/render** | Fresh disposable episode/API 8131, actual main code, official Studio, source edit, real asset uploads, render and full QC/decode | **PASS unattended** | [Main render](evidence/main-render-results.json); 4.923s, 1080x1920/30fps H.264/AAC, exactly narration + instrumental |
| **Production protection** | Public/pinned SHA-256 checks, approval/export records, no active jobs | **PASS** — 172 public files and 29 pinned files unchanged | [Protection results](evidence/production-data-protection.json) |
| Live AI | Real authenticated Codex/Claude response | NOT TESTED | No paid/live generation request was invoked |
| External analytics | Authenticated Meta services | NOT TESTED | Existing actual local metrics preserved, no invented values |

The complete suite was rerun on the final candidate rather than reused from the earlier rehearsal. Candidate application/backend source matches merged main. Focused backend tests and all frontend checks were rerun from actual main, followed by separate production-origin browser verification and a fresh actual-main disposable native render.

### Failures and remaining limits

The browser workflow initially timed out because five seconds was insufficient for complete pinned-document imports and concurrent native verification. It now waits for the real generation action to finish and allows bounded 30-second confirmation. Final workflow checks passed without fabricating results or changing application behavior.

Candidate Vite initially started while dependency installation was still finishing and reported an unresolved lucide-react scan. Restarted only that disposable Vite after installation; subsequent clean builds/browser checks passed.

The candidate's first draft recorded `Conflicting episode operation is already running` during simultaneous asset operations. Existing locks failed closed; the scanner retried and completed the editable draft. That failed record was retained.

Candidate rendering finished its frames but a Remotion Windows `taskkill` helper hung after its browser target exited. Verified ownership and absent target, terminated only that orphaned disposable helper, and the unchanged renderer continued through normal QC to completion. No isolation grants or engine code changed. **Actual-main native rendering subsequently completed without intervention.** Monitor this intermittent Windows cleanup issue.

Live AI authentication/generation, external Meta data, physical trackpad/touch hardware, acoustic alignment, licensing and subjective creative quality remain unverified. ZIP/folder downloads and generated-document uploads remain unsupported; selected files download individually. These are disclosed limitations, not a blocked merge.

## Production safety and recovery

The consistent SQLite backup (SQLite backup API) and prior dashboard build are retained outside Git at `E:/facebook/artifacts/merge-backups/20261106-122226/`. The verified source-history bundle including preservation is at `E:/facebook-integration-20261106/artifacts/integration/preserved-main.bundle`. No backup was deleted.

Restarted the normal production listener only after checking zero active AI/render jobs. Used `E:/facebook/scripts/start.ps1 -NoBrowser`, the original environment and production store; no manual-test provider override was applied to production. The backend on 8123 serves the actual main build. Existing media runtime, signature music and private configuration were not replaced with disposable state.

Production browser verification used GET/navigation/file playback and download. Upload/approval/render mutations used disposable stores only. The genuine episode remains COMPLETE; all 172 original public files, 29 pinned input files, approval SHA and export records remain unchanged. Normal read-derived index maintenance is not an approved-script rewrite.

If recovery is necessary, preserve newer work first and rehearse a normal reviewed `git revert -m 1 b23c202` in a separate recovery branch, retaining preservation `1852335`. Reinstall/rebuild from the reviewed source and restart only without active jobs. Never reset/clean production, restore a backup over newer work, or repin approved episode inputs. Backups are recovery resources, not automatic overwrite instructions.

The old `verify-redesign-snapshot.py` describes the original dirty pre-preservation HEAD/status. Those historical assertions no longer describe merged main; the manifest remains unchanged for provenance, and current preservation ancestry/tree/runtime evidence is recorded here.

**MERGED — LIMITED VERIFICATION**
