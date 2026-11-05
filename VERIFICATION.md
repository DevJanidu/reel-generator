# Executed verification - 5 November 2026

This report records actual local runs against disposable stores. The existing dashboard and Remotion composition were extended, not replaced. Genuine owner episodes were not used for tests. Reserved provider diagnostics are not production Reels.

| Check | Executed result |
|---|---|
| Automated suite | **53 passed** in 73.58 seconds, including the original 32 tests; one nonblocking Starlette TestClient/httpx deprecation warning |
| Frontend and video types | `npm run build` and `npm run typecheck` passed after the final UI changes |
| Official inputs | Four complete canonical documents, original-copy hashes, versions, lengths, order, master, overrides and context bounds validated; actual assembled model input inspected with mocks |
| Mandatory failures | Missing, unreadable, empty, truncated, wrong hash/version, invalid UTF-8, context overflow and incomplete model responses fail; no fabricated successful loads |
| Provider detection | Codex CLI 0.166.0 and Claude Code 2.1.318 detected; authentication is distinguished from integration eligibility |
| Live Codex workflow | HTTP-driven **10 ideas -> selection -> script -> internal review -> one explicit disposable test approval -> automatic preparation** passed; **18** image-only scene jobs; all required documents present; AWAITING_ASSETS; approved narration unchanged |
| Live connection buttons | Codex returned a validated nonce/JSON response with all four full skills and master. Claude reported AUTHENTICATION because no supported bare-mode API credential was configured. Manual reported readiness without a model call. Unconfigured API reported AUTHENTICATION |
| Real parallel Codex | Two simultaneous short opening-line requests in independent episode workspaces returned the correct distinct episode/character identities; 18.98 seconds overlap; shared hashes unchanged. This was not two full Reels |
| Native isolation | Two concurrent Windows MXC workers passed actual denied-write attempts and token checks: AppContainer true, elevated false. Authorized own-root writes succeeded |
| Adversarial paths | Shared master, skill, music, Remotion, root, sibling, cache, traversal, absolute path, junction, new external hard link, immutable snapshot/provenance rename, inherited subprocess and sibling deletion/rename attempts blocked |
| Controller separation | Worker controller-capability reads denied; mutations require the owner's local capability. Worker global SQLite access blocked; authoritative status/progress is episode-local |
| Locks and recovery | Same-episode cross-process conflict blocked; concurrent preparation commits serialized; duplicates, retries, interrupted requests, local state and child-tree cancellation tested |
| Pins and private state | Source/template/music versions pinned; changed globals do not repin existing episodes. Different instrumental replacement rejected. Private runtime files not downloadable; temporary Codex auth homes removed |
| Manual regression | Full manual request/import and owner draft flow passed through HTTP/UI; no AI success claimed for manual import |
| Browser | Desktop/mobile flow, no runtime errors/overflow, skills validation, provider controls, script approval, preparation import, Flow download and missing-file feedback passed |
| Assets | Bulk upload, image decode/ratio/scene matching, actual audio duration, SRT syntax/text/bounds, ambiguity, duplicate tracks and stale decode-cache replacement tested |
| Isolated synthetic render | Existing Remotion pipeline produced real preview and final under MXC, then automatic QC/export without another approval |
| Actual encoded file | FFprobe: **1080x1920, 30 FPS, H.264, AAC**; full decode and black-frame checks passed |
| Measured audio | Final **-16.01 LUFS**, **-2.49 dBTP**, measured speech/instrumental integrated gap **20.99 dB** |
| Sampled frames | Static illustration-region mean decoded difference **0.000712/255**; caption entrance **17.945/255**. These samples support static artwork and changing typography; they do not prove artistic perfection |

## Retained evidence

- `artifacts/cli-workflow/latest.json`: real Codex lifecycle, 18 scenes, exact approved narration, isolation and credential cleanup. Store: `artifacts/cli-workflow/20261105-213350/`. This run pinned master 1.0.0; later connection/parallel tests loaded the updated 1.1.0 master.
- `artifacts/parallel-cli/latest.json`: two real concurrent Codex requests, separate IDs and characters, verified boundaries and shared integrity. Store: `artifacts/parallel-cli/20261105-222421/`.
- `artifacts/isolation-smoke/latest.json`: actual permission results, tokens, child cancellation, locks and link defenses. Store: `artifacts/isolation-smoke/20261105-221959/`.
- `artifacts/render-smoke/latest.json`: isolated **4.922767-second synthetic** render and measured QC. Store: `artifacts/render-smoke/20261105-221422/`; final MP4 is inside its episode's `07_export/final/`.
- `artifacts/ui-smoke/latest.json`: desktop/mobile screenshots, original workflow checks and live provider-button results. Store: `artifacts/ui-smoke/2026-11-05T16-34-55-513Z/`.

Each fixture retains episode-local request/response/provenance, status, logs and relevant outputs. Live CLI calls consume the configured account's usage. Ordinary pytest uses mocks and does not consume model usage.

## Reproduction

```powershell
.\scripts\verify.ps1
.\scripts\verify.ps1 -Security -Render
.\scripts\verify.ps1 -CLI
.venv\Scripts\python.exe scripts\parallel_cli_smoke.py
node scripts/ui-smoke.mjs --providers
```

The CLI/provider commands intentionally make real calls. Read AI_PROVIDERS.md and SECURITY.md before changing authentication, isolation or native media runtime settings.

## Limits and resolved issues

- Claude's installed subscription login was detected, but automated Claude generation was not executed successfully: this adapter's documented bare mode requires intentionally configured API authentication. Subscription credentials are never extracted or routed. Manual Claude use remains available. No configured OpenAI-compatible API was available to test live.
- The real Codex creative test and synthetic render are separate fixtures. No genuine 45-75-second ElevenLabs/Google Flow production Reel was rendered. Approval in fixtures is explicit test-harness authorization, not the owner's approval for publishing.
- Native testing exposed a pre-existing hard-link alias risk. Production now rejects all pre-existing hard links/reparse points before launch; the writer separately rejects them. Real native tests also block creating new external aliases. Integrity hashes supplement permission tests rather than replace them.
- Remotion's bundled dynamic FFmpeg/FFprobe crashed under MXC on this machine. The existing renderer now uses a hash-pinned, read-only native runtime prepared during development from installed static tools. A reviewed compatibility launcher translates removed FFmpeg 9 filter-script flags and selects native AAC. Actual isolated rendering passed after this change; no second renderer was introduced.
- Application outputs/temp/cache are episode-local. Windows MXC itself provisions private OS container/bootstrap state; that is not claimed to be episode deliverable storage. Unsupported isolation fails closed. Default AI concurrency remains one; real two-worker tests justify optional higher concurrency, not unlimited parallel execution.
- Word-level forced alignment is not bundled. Trustworthy short phrase SRT cues and authored safe regions remain necessary. Syntax/text/bounds checks do not independently prove acoustic synchronization or correct face/clue detection.
- Audio measurements were executed. Subjective phone/headphone listening, instrumental/vocal classification, rights verification, story originality and creative satisfaction still benefit from human review. No supplied signature instrumental or license was invented.
- Scientific references preserved in the source documents were not all independently reverified in this integration. No audience retention curve, Meta access, publishing action or guaranteed performance is claimed.
- Documentary/Vertical Series regressions do not apply: this standalone application never contained those modes.
