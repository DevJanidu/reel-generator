# ODD FRAME - Reel Workflow Station v1.0

Small Stories. Big Emotions. Existing local Windows station for original cinematic 2D Facebook Reels. The dashboard and Remotion composition are preserved. Direct CLI providers and native episode isolation have been added; no older engine, Docker, hosted database or automatic publishing is used.

## Launch

This installation is configured to prefer Codex CLI with one AI job at a time.

```powershell
cd E:\facebook
.\scripts\start.ps1
```

The dashboard is http://127.0.0.1:8123. Use the launcher to open it: it supplies the local controller capability to the browser without exposing AI credentials. A bare URL remains readable but cannot authorize mutations without that browser session. Ctrl+C stops the controller; its worker Job Objects terminate children. Restart resumes deterministic renders and makes interrupted AI calls explicitly retryable.

For a fresh installation:

```powershell
.\scripts\setup.ps1
```

Tested environment: Python 3.14.7, Node 24.22.0, FFmpeg/FFprobe 9.0.2, Codex CLI 0.166.0 and Claude Code 2.1.318. Automatic workers require Windows 11 with working native MXC support; this machine passed actual probes. Setup installs locked packages, downloads Remotion's browser and prepares the shared media runtime using the built-in Windows .NET Framework C# compiler. Unsupported isolation never falls back to unrestricted workers. Manual creative import stays available.

## First Reel

1. Settings: choose Codex CLI and Test AI Connection. It must pass real structured generation plus native isolation. No separate API key is required for the existing supported ChatGPT Codex login. See AI_PROVIDERS.md for authentication details and Claude eligibility.
2. Create New Reel reads the complete four skills/master and queues ten concepts. Progress/errors/cancel/retry are real. Select a concept to create an isolated episode and automatically queue script writing plus internal retention review. Custom premises may skip ideation.
3. Script Studio: edit the reviewed narration, then APPROVE SCRIPT & CONTINUE once. Exact wording/hash/version is frozen and validated auto-export authorized.
4. The provider automatically generates and validates Character Bible, continuity, provisional storyboard, retention audit, narration, still prompts, image-only Flow JSON, manifests, caption/music plans and publishing draft. No separate artifact approvals. The episode becomes Waiting for Assets.
5. Google Flow Prompts: download IMAGE_JOBS.json or batches. Generate strictly 2D stills externally and save scene IDs such as S001.png.
6. Asset Manager: import stills, one ElevenLabs narration, trustworthy 1-4-word SRT cues split at scene boundaries, and one instrumental if no signature was configured. Record instrumental declaration and rights evidence. A validated instrumental is pinned. Global changes cannot replace it.
7. Refresh Assets or wait for scanning. Native-isolated validation queues the existing Remotion/FFmpeg pipeline automatically when gates pass. Static illustrations, purposeful cuts, animated white/black center captions and exactly narration plus instrumental. No image/character animation and no SFX.
8. Preview, technical QC and final 1080x1920/30 FPS H.264/AAC export run under the script authorization. Download in Exports. Correct actual safe regions in Edit Studio if necessary; no approved narration changes. Nothing publishes to Facebook.

Manual is an explicit fallback in Settings: download the complete request/schema, use your own AI tool and import JSON. Writing import creates the internal-review handoff. Owner-authored drafts can also be saved; AI review is not falsely claimed.

## AI configuration

```dotenv
ODD_AI_PROVIDER=codex_cli
ODD_CODEX_COMMAND=codex
ODD_CLAUDE_COMMAND=claude
ODD_AI_TIMEOUT_SECONDS=300
ODD_AI_MAX_CONCURRENT_JOBS=1
ODD_AI_CONTEXT_TOKENS=200000
ODD_AI_OUTPUT_TOKENS=12000
```

Settings stores provider/model/timeout/concurrency independently of environment defaults. Keep credentials only in environment/.env and restart after changes. Codex uses installed CLI authentication in a private short-lived job home, not a separate API integration. Claude dashboard automation uses documented bare mode and requires an intentionally supplied ANTHROPIC_API_KEY; subscription OAuth is not extracted/routed. Manual Claude use remains available. API mode retains explicit ODD_AI_BASE_URL, ODD_AI_MODEL and ODD_AI_API_KEY. No failure silently changes provider/billing.

Optional administrator music configuration: ODD_SIGNATURE_MUSIC, ODD_SIGNATURE_MUSIC_VERSION and ODD_SIGNATURE_MUSIC_RIGHTS. The selected global file is only read, then copied/pinned per episode. No music asset or license has been invented.

## Architecture and files

| Location | Responsibility |
|---|---|
| source_documents/ and four root uploads | Preserved original references |
| brand/references/ODD_FRAME_OFFICIAL_CONTENT_BIBLE_v1.md | Official Bible |
| brand/skills/ODD_FRAME_FANBASE_GROWTH_PSYCHOLOGY_SKILL.md | Psychology |
| brand/skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md | Full design guide, obsolete name normalized |
| brand/skills/ODD_FRAME_TYPOGRAPHY_AND_MOTION_GUIDE.md | Full typography source |
| brand/SKILLS_MANIFEST.json, ODD_FRAME_RULES.json | Versions, hashes, responsibilities and latest production overrides |
| prompts/00_MASTER_PROMPT.md and 01 through 11 stage prompts | Creative orchestration/contracts |
| apps/dashboard/src/ | Existing React/TypeScript/Vite/Tailwind UI |
| services/api/skills.py, snapshots.py | Full mandatory loader and immutable episode input versions |
| services/api/providers.py, scripts/cli_worker.py | Direct CLI/API/manual adapters and structured output |
| services/api/file_writer.py, isolation.py, windows_job.py | Scoped atomic writes, native permission/token probes, child lifetime |
| services/api/creative.py, models.py | Episode manager, schemas, review, approval and document compilation |
| services/api/media.py, worker.py, scripts/production_worker.py | Isolated validation, measured timing/audio and persistent rendering |
| services/api/core.py, main.py | Trusted controller/index, API, history, settings and downloads |
| video/remotion/ | Existing composition plus read-only, hash-pinned media runtime |
| episodes/OF_RNNN_slug/.production/ | Per-episode inputs, provenance, locks, runs, jobs, temp, logs, private runtime |
| production_status.json inside each episode | Authoritative production state/history |
| data/odd_frame.sqlite | Trusted controller's derived index/settings; workers cannot open it |

The whole application tree is not copied per episode. Only required creative inputs, small template sources and optional music are snapshotted. Global upgrades apply to new episodes. Existing pins remain stable; changed immutable inputs fail validation. Shared suggestions belong in episode reports, not automatic source patches.

The scoped writer rejects traversal/absolute/device paths, links and immutable overwrites. A verified non-elevated MXC AppContainer confines workers/children; native denial tests run before execution. The owner controller capability is inaccessible to workers, preventing localhost mutation bypass. Read SECURITY.md for the actual boundary, OS runtime details, link defenses and tested Remotion/FFmpeg compatibility.

## Verification

```powershell
.\scripts\verify.ps1
.\scripts\verify.ps1 -Security -Render
.\scripts\verify.ps1 -CLI
node scripts/ui-smoke.mjs --providers
```

Ordinary tests use mocks and consume no model usage. CLI/provider flags intentionally make real calls. Disposable stores remain under artifacts; genuine episodes are not modified. See VERIFICATION.md for executed results, evidence paths and limitations. Scientific claims preserved in sources are not automatically newly verified; no analytics/retention curves are fabricated. Exact acoustic alignment, art quality, licensing and listening remain separate from technical checks.

See HANDOFF.md, AI_PROVIDERS.md, SECURITY.md, WORKFLOW.md, AGENTS.md and workflows/REEL-*.md. Development uses npm run dev with API proxy; build uses npm run build and npm run typecheck.
#   r e e l - g e n e r a t o r  
 