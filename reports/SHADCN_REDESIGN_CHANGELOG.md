# ODD FRAME redesign changelog

## Current Asset Manager — folder explorer

Owner-requested Finder-style browsing now mirrors actual episode directories, including empty and nested folders. The default view opens `05_assets`; Images, Narration, Subtitles and Music have separate shortcuts. Other generated episode folders are available under All episode folders. List/grid views, folder breadcrumbs/back/up, current-folder search, natural name/kind/size/modified sorting, real file sizes/dates, text/image/audio/video previews and scoped downloads are provided through shadcn components. Import controls appear only in supported raw asset folders. Existing music rights, validation, protected inputs and upload/delete contracts remain intact; no files are moved or reorganized.

The sole backend extension after the source snapshot is a read-only public file catalog used by episode detail. `file_entries` adds actual directory/file metadata while retaining `files` for existing clients. The catalog excludes `.production` and temporary files and rejects links/aliases. This is required to show real empty folders; no database, worker, provider, creative or rendering changes were introduced. Deploy/restart this small API extension with the frontend. The source verification script explicitly checks this exception and compares the rest of the API module AST with the snapshot.

## Current theme — owner revision

The owner replaced Midnight Gold with the supplied neutral shadcn reference. The current app uses near-black backgrounds, neutral gray surfaces, rounded cards/inputs and white pill-shaped primary actions. Decorative gold has been removed from navigation, Ideas, activity, forms and Help. Green indicates confirmed success, red errors and yellow actionable warnings. Shared status badges apply the same semantics to episodes, Queue and Activity; running/queued work remains neutral. Production artwork, brand rules and creative-engine files are unchanged. The earlier gold styling described below records the implementation history, not the current palette.

## Baselines and boundaries

Original: main at af891b2d2a18f2fc103f312899adffd84f526a72 in E:/facebook.
Development: feat/shadcn-ui-redesign in E:/facebook-ui-redesign.
Owner-authorized reviewed snapshot: d445704. Setup: 6f86a0c. Routed shell/workflows: 225b536. Later polish and verification are separate commits.

The snapshot preserves the 42 modified paths, deleted custom editor, and 27 untracked source/configuration/test/documentation paths. SHA-256 records and classification are in SOURCE_SNAPSHOT.json and UI_AUDIT_SHADCN.md. No production databases, episodes, exports, caches, music, private environment or authentication files were copied. No backend, creative prompt, brand or Remotion engine changes were introduced after the snapshot.

## Official components

Configured the existing Vite workspace using [official existing-project instructions](https://ui.shadcn.com/docs/installation/vite), CLI 4.23.0:
`npx shadcn@latest init --base radix --preset nova --yes --no-monorepo`.
Used the official registry add command, not an unrelated scaffold.

Installed: Sidebar, Button, Card, Dialog, AlertDialog, Sheet, Tabs, Badge, Input, Textarea, Select, Command, Tooltip, Popover, Dropdown Menu, Table, Progress, Skeleton, Scroll Area, Separator, Switch, Slider, Accordion, Sonner, Breadcrumb, and the Input Group dependency. Registry component implementations remain intact. Product-level styling lives in semantic tokens and redesign.css. The official shared stylesheet is vendored as shadcn.css; the CLI is not shipped as an application dependency. The installed primitives use the unified Radix package; no second competing UI library was added. TanStack Table was not needed for the current simple queue table.

## Changes

- One official Sidebar shell, persisted expanded/icon preference, collapsed tooltips, mobile Sheet, clear active state, breadcrumbs and skip link.
- Fifteen page URLs with episode selection in a validated search parameter; refresh/back/forward restore state. Old editor URLs redirect to the official Studio launcher.
- Station, episode, run and Studio reads use Query observers and AbortSignal. Removed duplicate transport and overlapping fast/slow dashboard polls. Shared keys and targeted invalidation follow controlled actions. Existing form drafts remain editable local state.
- Typed station API contracts; multipart uploads retain browser boundaries; errors are normalized. Six transport tests cover authorization, cancellation, multipart, validation, empty and unreadable responses.
- Midnight Gold surfaces, readable typography and focus states. Owner-requested primary buttons use 12% gold fill, 20% hover fill and warm readable text. Reel links are transparent. Sidebar items have 6px gaps. Help rows use neutral surfaces and subtle open/hover gold. Legacy button styles exclude shadcn controls.
- Compact Home: real counts, recent Reels, next actions and jobs; unknown counts show a dash while loading.
- Preserved all eight category groups, 24 genres, five-idea batches, history, custom premises, manual imports and backend validation. Official Dialog provides focus management.
- Readable script editing and approved-wording controls; existing approval contract unchanged.
- Existing episode pipeline, Flow image-only exports, role-based asset imports, rights declarations, technical validation and file actions retained.
- Dedicated Queue displays backend jobs and separate AI/render capacity; no invented percentages.
- Activity uses an official Sheet and a dedicated page; existing allowlisted SSE events, elapsed time, errors and retry/cancel retained.
- Official Remotion launcher retained with Query-managed status, genuine readiness and rebuild/edit-preservation controls; no replacement editor.
- Exports retain download and current-episode QC actions; deletion uses AlertDialog. On-demand video uses the backend preview path or final file, with preload disabled. Per-export preview playback was not exercised against a newly rendered final.
- Settings and owner-entered Analytics retain contracts and gain readable forms. Help adds searchable A–Z sections and preserves the detailed prior job/audio guide. Health reports real controller/tool/skill information without claiming unverified isolation.
- Vite preview proxies only to disposable backend 8124; the backend explicitly accepts development origin 5174 through ODD_PORT. Host/Origin and capability enforcement are preserved.

## Preview

Open http://127.0.0.1:5174. Existing application source stays at E:/facebook.
Disposable preview state lives only in the feature worktree's ignored artifacts/preview-data.
To restart after stopping the existing preview processes, run `npm run ui:preview` in the feature worktree. It refuses occupied ports. ODD_DEV_PYTHON may override the development Python interpreter path. No original .env is copied.


## Ideas card correction

Category cards now use the official outline Button variant with explicit 18px card corners, contained 20?22px padding and a bottom-aligned genre count. They no longer inherit primary-action pill corners. At narrow mobile widths the category grid becomes a single readable column. Eight category groups, genre selection and generation behavior are unchanged. Targeted browser checks verify all child content stays inside every card at 1920, 1440, 768 and 390px, plus selected states and no horizontal overflow.


## Hover and spacing corrections

Reel rows and next actions use the ghost Button variant with a neutral, readable hover/focus surface rather than the primary white action hover. Secondary and text controls also use neutral hovers. The brand header cannot shrink under sidebar scrolling; the icon and label have separate bounds and the collapsed icon fits its 48px rail. Header status/provider/avatar items have an explicit 12px gap. Global alerts appear before page content with top/bottom spacing; authorization helper paths are readable. Short pages stay top-aligned. Production-history search tools and saved-session/generation-batch fields have consistent heading, label and input gaps.

## Dedicated Explorer follow-up

Asset Manager now contains production controls and its always-expanded checklist, with working Open File Explorer and Upload Files actions. The reused explorer fills `/episodes/:episodeId/files`, with separate folder/file scrolling and a mobile folder Sheet. Explicit upload destinations, transfer progress, duplicate/type/size validation and selected individual downloads use existing protected APIs. No backend changes or dependencies were added in this stage. ZIP downloads and generated-document uploads are unsupported. See [DEDICATED_FILE_EXPLORER.md](DEDICATED_FILE_EXPLORER.md) for verification, screenshots and limitations.

## Script editor gating and badge spacing

Script Studio now shows brief/narration editing and Save Edits only after a persisted script has a successful script/review run. Empty, queued/running without output, failed without output and owner-import-only drafts show generation guidance instead. Existing approved scripts remain readable and locked, including legacy approvals without run records; draft data is never deleted. Active generation/review disables editing/saving/approval. Backend approval and manual AI response import contracts are unchanged.

Standalone panel badges use a shared block layout with 12px top/16px bottom spacing. This separates NEEDS ASSETS from validation errors and also applies to isolation/other standalone badges; inline header/table badges retain their container spacing. Scene-chip groups retain an 8px gap and gain 16px separation from preceding content.

Verification: TypeScript/Vite build and 12 frontend tests PASS. scripts/script-editor-qa.mjs PASS with intercepted state/mutation fixtures (no provider calls or episode writes): pre-generation, running, failure, import-only, review lock, generated edits/save, approval payload and locked refresh/legacy approval. scripts/badge-spacing-qa.mjs PASS with measured gaps on Assets and Workspace at 1440px/390px; screenshots inspected and no horizontal overflow. Original source preservation verification PASS. Evidence: reports/evidence/script-editor-results.json, badge-spacing-results.json and validation-spacing-1440.png / validation-spacing-390.png.
