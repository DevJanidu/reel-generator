# Merge readiness

## Decision

Latest scope addition: Asset Manager now needs the paired read-only `file_entries` API metadata extension in services/api/file_catalog.py and the episode-detail handler. Existing `files`, upload/download/delete contracts, database schema and engine remain unchanged. The earlier no-backend-change statements below describe the initial redesign; this explicitly reviewed read-only feature is the only subsequent exception. Original E:/facebook remains unchanged.

Ready for owner UI review at http://127.0.0.1:5174. Not merged, pushed, rebased or deployed. Worktree retained. Owner approval and original-work reconciliation remain required before integration.

Original: main, af891b2d2a18f2fc103f312899adffd84f526a72.
Feature: feat/shadcn-ui-redesign, E:/facebook-ui-redesign.
Reviewed source snapshot: d445704; compare redesign changes against that commit, not only against main. The earlier owner backend/prompt/Remotion upgrades are in the snapshot and are not UI-engine rewrites.

## Verification

See UI_REGRESSION_TESTS.md. Dashboard and Remotion checks, 151 backend tests, six frontend unit tests, browser manual integration, responsive navigation and axe checks passed. Dependency audit is clean. Original main HEAD, dirty status and source hashes are checked by scripts/verify-redesign-snapshot.py.

Local main is still the original baseline and is an ancestor of the feature branch, verified with git merge-base. This establishes commit-graph compatibility with the current local target, not permission to merge into a dirty worktree. Remote-target freshness was not checked by fetching or changing refs. Future target changes require a new integration check.

No backend/database schema or creative-engine changes were introduced after snapshot d445704. No runtime stores, original episodes, source music, authentication files or private env files are tracked in the feature changes. Source uploads remain preserved.

## Reconcile the original uncommitted work before any future merge

The original E:/facebook still has the owner's 42 modified paths, one deletion and 27 untracked paths. Do not merge into it while dirty; do not stash, clean or discard it automatically.

With separate owner authorization, first preserve those reviewed changes as a commit on an owner-selected preservation/integration branch or establish another reviewed durable baseline. Compare every source file with reports/SOURCE_SNAPSHOT.json, and account for any owner edits made since this snapshot.

Then test integration in another isolated worktree. If the original changes have already been committed separately, apply only the redesign commits after d445704 to that reconciled baseline, under explicit owner authorization, so the owner-source snapshot is not duplicated. Otherwise review the full snapshot plus UI branch as the intended integration. Resolve any differences explicitly, run the regression checks and compare screenshots again. Do not silently overwrite newer owner work.

Only after owner approval should the chosen integration be applied to the target branch. No automatic merge action is part of this task.

## Migration and rollback

No data migration is required. The existing APIs, immutable episode versions, approved narration, engine and official Studio workflow are preserved.

Before authorized integration, retain the original build/source baseline and production-data backups using the station's normal owner workflow. Build the approved frontend from its lockfile and verify local Host/Origin/capability configuration. The development proxy intentionally targets only disposable backend 8124 and must not be mistaken for production configuration.

Rollback the frontend by restoring the prior approved source/build in a clean authorized integration environment; do not reset the dirty original worktree. Do not roll back or repin episode inputs, assets or approvals. Keep the development worktree for comparison until the owner decides otherwise.

## Remaining review items

Human approval of the UI, actual screen-reader review, other browser engines, runtime performance profiling, live provider calls, three automatic native workers and a fresh full production render are unverified. New preview playback against a newly rendered final is also unverified. These limits are distinct from the passing existing regression suite. No creative quality, rights or analytics claims are implied by UI tests.

