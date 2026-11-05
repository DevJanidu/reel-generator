# ODD FRAME Live Studio upgrade

Implemented on `frontend-ui-changes` as an extension of the existing station. The FastAPI controller, creative workflow, provider adapters, episode writer, native MXC boundary, measured audio pipeline and Remotion renderer remain in use. No Next.js application was introduced.

## Launch

Production dashboard: restart the FastAPI station, then run `./scripts/start.ps1` from `E:\facebook`. An already running controller must restart to load upgraded Python routes. This opens `http://127.0.0.1:8123` with the existing controller capability. Keep the controller running while jobs execute.

Development frontend: run the existing FastAPI controller, then `npm run dev` and `./scripts/open-dev-browser.ps1`. Vite proxies `/api` to port 8123. The development browser launcher gives the Vite origin its own authorized session; sessionStorage is origin-scoped, so an 8123 launch alone cannot authorize 5173. Credentials are never embedded in frontend source.

The new typed route is `/episodes/$episodeId/editor`, using the numeric episode ID. Deep links and refreshes work through FastAPI's SPA fallback. `/help` explains AI progress and live-versus-final audio behavior. Use **Edit Studio → Auto Edit → Open Live Editor**, or the completed draft's **Open Live Editor** action in AI Activity. Valid newly supplied assets also queue the draft automatically.

## Installed foundation

The station already had Vite 8.3.6, React/React DOM 19.2.4, TypeScript, Tailwind 4, FastAPI and Remotion 4.0.541. Only the missing `@tanstack/react-query`, `@tanstack/react-router` and `@remotion/player@4.0.541` were added. Remotion Player is version-matched to the renderer and bundler. The application and editor are separate Vite chunks, about 368 kB and 400 kB uncompressed in the verified build.

| File | Responsibility |
| --- | --- |
| `apps/dashboard/src/main.tsx` | Existing dashboard, retained features and Query-backed episode/status loading |
| `apps/dashboard/src/router.tsx` | Typed TanStack routes, Query provider, lazy editor loading, persistent Activity Monitor |
| `apps/dashboard/src/editor.tsx` | Remotion Player, four tracks, transport, inspectors, two audio channels, undo/redo, autosave and revision restoration |
| `apps/dashboard/src/activity.tsx` | Global/episode job monitor, safe milestones, generated files, supported actions and help |
| `apps/dashboard/src/api.ts` | Controller-authorized editor requests |
| `apps/dashboard/src/studio.css` | Midnight Gold layout, resizable player/inspector and responsive timeline |
| `services/api/editor.py` | Deterministic draft preparation, waveform decoding, strict edit schema and revision persistence |
| `services/api/activity.py` | Bounded episode-local journals, safe provider-event normalization, SSE replay cursors |
| `services/api/worker.py` | Separate draft/render jobs; native worker execution and real frame callbacks |
| `scripts/cli_worker.py` | Async provider stdout parsing, bounded output and safe status emission |
| `video/remotion/src/composition.tsx` | Shared actual OddFrameReel component for Player and final export |

The Remotion entry point now registers the shared composition. This is an owner-authorized development refactor; episode workers never edit shared source. Existing historical input snapshots remain unchanged. New editor drafts carry an explicitly versioned, hash-checked episode-local runtime under `06_edit/remotion/editor-v1`. Preview refuses a mismatched installed runtime instead of silently displaying a different engine. New episode snapshots include the shared component; explicit profile adoption includes it as well.

## Automatic assembly and editing

Auto Edit consumes the approved narration, storyboard, supplied subtitle timings, validated Flow stills, pinned style and instrumental. Existing deterministic scene timing, safe-caption placement, phrase grouping, authored emphasis and transition rules produce the draft. Higher-level editorial decisions already come from the schema-validated creative package; no model is called for each caption or frame.

The isolated worker measures/normalizes narration, ducks/balances the continuous instrumental and decodes real waveform peaks. All four tracks are populated before `EDIT_READY`. No preview/final MP4 or Remotion bundle is required for opening or adjusting the live draft.

The Player and export use the same component and saved frame-based properties. Scenes remain static; supported profile transitions are cuts, crossfades and dips to dark. Cinematic captions expose Wave Reveal, Glow Pop, Smooth Phrase Replacement, Immediate Impact and Soft Fade with bounded size/position/glow/animation controls. Legacy Classic profiles retain their original options; adopt Cinematic Flow explicitly in the existing dashboard before rebuilding to enable its controls.

The narration and already measured instrumental bed remain separate sources. Live gain, additional fades and additional narration-envelope ducking are shared composition properties. Mute and solo are audition-only. The source-peak indicators use decoded audio peaks and the known frame controls, not an assertion of measured device output. Final FFmpeg integrated-loudness/true-peak mastering remains in place and can change overall loudness relative to browser audition.

## Persistence and security

Episode-local files include `edit_plan.json`, `timeline.json`, `captions.json`, `audio_mix.json`, `waveforms.json`, `editor_state.json`, `audio/draft-<job>/` and `revisions/`. The state file points to an immutable saved revision; compatibility mirrors cannot override that committed pointer. Saves use the existing scoped writer, media/editor locks and optimistic revision checks. Autosave is debounced by 1.2 seconds. Current-session undo/redo is bounded; saved revision history survives refresh. Restoring a revision creates a new edit rather than overwriting history.

Rebuild is explicit after changed assets or settings. It archives the prior plan, retains previous revisions and prepared audio, and queues a new isolated deterministic job. The watcher does not silently replace an existing saved draft.

The backend rejects arbitrary paths/properties, story or scene-order changes, non-finite gains, unsupported transitions, caption/protected-region collisions, stale source fingerprints and stale revisions. Caption timing corrections are limited to two frames from supplied cues; approved narration remains locked. Final export rechecks authorization, source hashes, prepared audio hashes and runtime hashes, then records the saved revision and timeline hash in QC. Public file/media endpoints reject private `.production` paths, including Windows case aliases and links. No publishing was added.

## AI Activity

`GET /api/activity` restores recorded jobs. `GET /api/activity/stream` emits SSE with a per-job sequence vector in the event ID. Reconnects replay unseen retained events; gaps beyond the bounded journal trigger resynchronization. Journals retain up to 600 events per job inside its assigned root. The controller derives the global view from its index; workers never open the global database.

Codex uses its installed `exec --json` JSONL output. Claude uses its installed `--output-format stream-json --verbose` mode and supported configured authentication, following the [Codex noninteractive documentation](https://learn.chatgpt.com/docs/non-interactive-mode) and [Claude programmatic execution documentation](https://code.claude.com/docs/en/headless). Stdout is drained asynchronously, stderr is written privately under the episode, and event size/total capture are bounded. Only fixed allowlisted status messages reach the public activity stream. Provider text, thinking, token deltas, tool arguments, credential contents and private job homes are excluded. Unexpected tool activity still rejects the response.

AI stages show real labels and elapsed time. Remotion supplies actual rendered-frame counts. Asset completion reports real validated counts. There are no invented AI completion percentages. The global monitor persists across routes, supports episode filtering and shows supported AI Cancel/Retry actions, retry ancestry, files, milestones and last event time. Render cancellation is deliberately not offered because no corresponding backend operation exists. A silent provider gets an explicit no-detailed-progress message.

## Verification evidence

- Original upgrade verification: **89 tests passed**, recorded in `artifacts/studio-upgrade/pytest-complete.xml`. Merge verification on November 6: **90 tests passed**, recorded in `artifacts/merge-main/pytest-main.xml`, including saved-edit export retry and failed-rebuild recovery. The remaining warning is the existing Starlette/httpx TestClient deprecation.
- Additional episode-local draft, revision, stale-input, runtime-integrity, replay, multi-episode and cancellation checks use synthetic fixtures and mocked provider execution. Ordinary pytest cannot launch an async live CLI provider.
- `npm run build` and `npm run typecheck` pass.
- Existing dashboard browser workflow passed, including desktop, 390px mobile, manual package import, approval, Flow download and native missing-assets feedback: `artifacts/ui-smoke/latest.json`.
- Real episode copy: 18 scenes, 82 captions, 3,194 frames (106.47 seconds). Native draft preparation took 39.5 seconds for Classic and 39.0 seconds for an explicitly adopted cinematic copy. No MP4 existed before the render action. Original episode hashes were unchanged.
- Browser tests on that cinematic copy: editor loads measured 1.28–1.37 seconds, with 98–103 advanced frames over a 3.2-second observation plus click overhead, independent narration/music elements, music volume changed to 0.35 immediately, caption DOM preset changed live, transition/save/refresh/undo/redo passed, zero render requests during adjustments, zero browser runtime errors. Initial SSE replay returned 19 distinct events; the post-render repeat replayed 434 events. Both resumed with zero duplicates. These are single-machine observations, not playback guarantees.
- Real Codex CLI 0.166.0 activity appeared in the browser while the diagnostic ran. Its exact structured response passed after full pinned-input loading. Authorized Claude Code 2.1.318 also passed a real streamed diagnostic. These are explicit live checks, separate from pytest mocks.
- Native adversarial verification passed with two parallel MXC workers, denied shared/sibling/controller writes/reads, rejected existing aliases, cross-process locks and cancellation killing descendants: `artifacts/isolation-smoke/latest.json`.
- Merge preparation also verified the staged source bytes against the working files and preserved 91 protected input/episode files by hash. `.gitattributes` disables line-ending conversion so Windows checkouts retain the exact bytes required by production provenance. Local credentials, episode data, media caches and exports remain ignored. The environment example contains empty credential fields. The source-refactor helper is idempotent, and launch/test helpers do not request execution-policy bypasses.
- The saved browser-edited revision 3 exported successfully at 1080×1920, 30 fps, H.264/AAC: 3,194 frames / 106.47 seconds. Complete decode, black-interval, codec, duration and loudness checks passed; measured output was -16.01 LUFS and -3.79 dBTP. The complete isolated preview/final/QC/export job took 447.49 seconds. `artifacts/studio-upgrade/latest-render.json` records the revision and saved timeline hash. An initial copied-episode fixture lacked `07_export/final`; the exporter now safely recreates that assigned directory before committing the versioned file.

Useful explicit checks: `python scripts/studio_verify.py --prepare-real --cinematic`, `node scripts/studio-ui-smoke.mjs --providers`, `python scripts/isolation_smoke.py`. Run these with the station's virtualenv and native host authorization. `--provider`/`--providers` consume real provider usage; ordinary tests do not.

## Remaining limits

- The timeline supports frame scrubbing, phrase-level timing corrections and contextual controls. It does not implement free-form drag/trim editing or reordering approved storyboard scenes.
- Music ducking starts with the existing measured FFmpeg bed. Live ducking is an additional deterministic envelope, not a browser recreation of FFmpeg's sidechain compressor. Meters are decoded source estimates. Listening and final mastered-media checks remain necessary.
- Audio-only video-stream reuse was investigated using [Remotion's encoding documentation](https://www.remotion.dev/docs/encoding#audio-only-export). Remotion supports audio-only codecs through the same composition; a future optimization can hash the visual props/runtime/assets, render only the changed audio and remux against a verified cached H.264 stream. That optimization is not enabled: current final jobs render the full saved composition and then stream-copy video during mastering. No unverified cache reuse is claimed.
- Historical drafts require their matching installed editor runtime to preview. Automatic runtime repinning is blocked. Existing Classic episodes stay Classic until explicit adoption/rebuild.
- SRT acoustic accuracy, licensing, vocal absence, artistic quality and audience performance are not proven by machine checks. No forced-aligner or real analytics were fabricated.
