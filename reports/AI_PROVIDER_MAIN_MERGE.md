# AI reliability — local main integration

Status: **MERGED — LIMITED VERIFICATION**. The local merge and source/build checks passed. Production services were not restarted and no live model request was made; runtime activation and live provider execution are not claimed.

- Original main: `4781f23aa6045824dddcb80f760c05d89f61fd8f`.
- Reliability feature: `71574429ac77de05d77e7447e84cd9e527341f1a`, `fix/ai-progress-retry`.
- Merge commit on main: `847023860fa8bc62eb4c9f1ea3c93f675770cebc`.
- Rehearsal: `integration/ai-reliability-20261106`, worktree `E:/facebook-ai-merge-20261106`.
- Original reliability worktree: `E:/facebook-ai-reliability`, retained.

The isolated normal merge had no conflicts. Its complete tree exactly matched the previously tested feature tree, `0b690eac99b5cfa2440a5adb73ad820bce27a516`. Five focused backend tests passed in the rehearsal before committing its two-parent merge. Main was then updated by a normal fast-forward to that verified merge commit. This documentation commit follows the code merge; inspect `git log -2` for the final documentation tip.

Only the reliability fix was integrated. The storytelling branch remains separate. No push, destructive cleanup, stash, reset, dependency upgrade, database migration, credential change or production restart was performed. Main's untracked owner specifications under `feat/` were reviewed as nonoverlapping, preserved and left uncommitted.

## Checks from actual main after merge

| Check | Result | Evidence |
|---|---|---|
| Dashboard TypeScript + Vite production build | PASS | `artifacts/ai-main-merge/build.log` |
| Frontend tests | PASS: 13 tests | `artifacts/ai-main-merge/frontend-tests.log` |
| Remotion TypeScript | PASS | `artifacts/ai-main-merge/remotion-typecheck.log` |
| Backend smoke checks | PASS: 5 tests | `artifacts/ai-main-merge/backend.log` |
| Production preservation | PASS, with generated-report refresh noted below | `artifacts/ai-main-merge/preservation.json` |

Backend smoke checks exercise actual fake-CLI incremental streaming, retry/error/approval preservation, correct package completion labeling and both Claude authentication adapter modes. All mutations use disposable test roots. The existing httpx test-client deprecation warning remains. Earlier complete regression, failure-injection and browser/SSE evidence is documented in [the implementation report](AI_PROVIDER_RELIABILITY.md); it was not relabeled as a new complete-suite run on main.

No queued/running production AI or render jobs were present immediately before updating main. Before/after hashes cover 204 episode, pinned-input, specification and environment files. 203 remained identical. The sole changed file was OF_R002's generated `reports/ASSET_VALIDATION.json`, containing a fresh `checked_at`, consistent with the running asset-validation workflow. It was inspected as a generated diagnostic, not restored or overwritten. All other protected files, SQLite episode statuses, approved-script hashes and export records remained unchanged. The owner specifications and `.env` hash remained unchanged. SQLite was inspected read-only, not copied or replaced.

OF_R002 retains its successful 20-scene production package and approved script and remains at its existing asset-blocked stage. Continue through the actual Asset Manager checklist; this merge does not regenerate it.

## Activation and recovery

Restart ODD FRAME through its normal startup procedure when ready to load the new Python backend, then refresh the dashboard. The production frontend assets have been rebuilt from main. Existing running Python processes are not claimed to have loaded the new code. No paid provider diagnostic was run.

If a rollback is needed, review a source-only revert of merge `8470238` using its first parent as the baseline; do not hard-reset or replace episode data, SQLite, credentials or media. Keep the feature and integration worktrees and verify that any newer production source changes are preserved before reverting. No rollback was executed.
