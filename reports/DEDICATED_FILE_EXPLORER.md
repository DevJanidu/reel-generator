# Dedicated Episode File Explorer

Implemented on `feat/shadcn-ui-redesign` in `E:/facebook-ui-redesign`. The original `E:/facebook` worktree remains on its unchanged, dirty `main`. Nothing was merged, pushed or rebased.

## Architecture audit and change

Asset Manager previously embedded `AssetExplorer` below production controls and the expanded `PipelineTracker`. This put an internally scrolling two-pane explorer inside the main page scroller. The existing explorer already provided real episode metadata, navigation, search, sort, previews and file actions; these were reused rather than replaced with a second browser.

Asset Manager now retains its active Reel selector, permanently expanded production checklist, real asset counts/validation, missing-asset warnings, automatic monitoring, Refresh Assets and music declarations. Open File Explorer navigates to `/episodes/:episodeId/files`; Upload Files opens that same episode's destination dialog. Direct navigation, refresh and browser Back/Forward preserve the episode.

The dedicated route fills the application content area. The toolbar remains outside the file-list scroller. The application sidebar, desktop folder sidebar and right file-list viewport each have their own constrained scrolling boundary. Flex children have `min-height: 0` and appropriate `min-width: 0`; native overflow and overscroll containment prevent chaining. The page itself does not add a fourth vertical scrolling region. Mobile uses an official shadcn Sheet for folders. No wheel blockers or global event handlers were introduced.

## Functionality and security

- Real folder hierarchy, empty/nested folders, breadcrumbs, Back/Up, search, ascending/descending sort, list/grid views and refresh are preserved.
- List checkboxes support multiple file selection and individual downloads. Filename actions open previews; folders also support double-click.
- Image/audio/video previews and bounded plain text/SRT/JSON previews reuse the existing Sheet and episode file endpoint. Text is not rendered as HTML.
- Uploads explicitly identify the Reel and `05_assets/{images,narration,subtitles,music}` destination. Multiple selection, destination-folder drop, extension/size checks, duplicate cancellation and actual byte-transfer progress are provided. Transfer completion is distinguished from backend confirmation. Successful mutations invalidate/refetch the existing backend state.
- Existing server upload rules remain authoritative: approved/prepared episode requirements, render locks, scene-image naming, 512 MiB limit, allowed extensions, controller/Origin enforcement, no silent replacement and episode-scoped EpisodeWriter validation.
- Existing read-only catalog and download path protections remain in place. No unrestricted filesystem endpoint, new backend endpoint, schema change, worker or dependency was added for this task.

## Verification

- Dashboard strict TypeScript check and Vite production build: PASS.
- Frontend unit tests: 12 PASS.
- Relevant catalog/export/API-path-safety backend regressions: 8 PASS using disposable test storage.
- `scripts/dedicated-files-qa.mjs`: PASS, manager separation, expanded status, episode route, refresh/Back/Forward, selected download, invalid/duplicate cancellation, mobile drawer and full-height layout.
- `scripts/asset-explorer-qa.mjs`: PASS, actual folder browsing, sort/search, views, text/audio preview, real multipart narration upload and byte-identical download, remove cancellation, private-folder exclusions and desktop/mobile layouts. Axe: zero violations on the checked populated Explorer.
- `scripts/scroll-isolation-qa.mjs`: PASS, real overflow from 80-folder/80-file response fixtures, independent scroll positions, boundary containment and keyboard scrolling at 1920x1080, 1440x900, 1366x768, 1024x768 and 390px mobile.
- Original source preservation check: PASS, original HEAD, branch, status and reviewed file hashes unchanged.

Browser tests used actual Chromium against the disposable preview API, not production episode mutations. Trackpad hardware and physical touch devices were not independently exercised. No real provider or new final render was invoked.

## Evidence and review

- Preview: http://127.0.0.1:5174/assets (choose a disposable Reel, then Open File Explorer).
- [Desktop](evidence/dedicated-files-desktop.png), [mobile](evidence/dedicated-files-mobile.png), [route results](evidence/dedicated-files-results.json), [scroll results](evidence/dedicated-files-scroll-results.json).
- Changed UI modules: `api.ts`, `router.tsx`, `main.tsx`, `app-sidebar.tsx`, `asset-explorer.tsx`, `redesign.css`; browser regression scripts and this review package.

## Limitations

ZIP/folder downloads are not implemented because the existing API does not support them. Multiple selected files download individually and browser multiple-download policy may require permission. Document/JSON uploads are not enabled: generated/approved project documents remain read-only; existing pipeline asset types alone can be uploaded. Folder Forward history is not implemented; browser Back/Forward works for application navigation. The explorer does not persist its current inner folder in the URL.

Ready for owner UI review, with these limitations. Before any future authorized merge, reconcile the original dirty source against `SOURCE_SNAPSHOT.json` in a separate integration worktree as described in `MERGE_READINESS.md`; do not overwrite or reset the owner's uncommitted work.
