# ODD FRAME upgrade handoff

The EXISTING station in E:\facebook has direct CLI providers and native episode isolation. Its dashboard, story workflow, single approval and Remotion composition are preserved.

Launch: cd E:\facebook then .\scripts\start.ps1. Opened dashboard: http://127.0.0.1:8123. Settings is configured for codex_cli, timeout 300 seconds and one AI job. Test AI Connection performs a real full-instruction short request, not a file-existence test. AI_PROVIDERS.md explains all four providers and actual Claude authentication eligibility.

The real Codex workflow passed: ten ideas, selection, narration/script, internal review, one test-harness approval and automatic Character Bible, continuity, storyboard, ten-criterion retention audit, narration and 18 image-only Flow jobs, ending AWAITING_ASSETS. No manual copying was used in that automatic run. Its genuine production release was not authorized; it is a disposable test project under artifacts.

The isolated synthetic Remotion regression also passed: real preview and 1080x1920/30 FPS H.264/AAC final, measured two-source audio, full decode and static-image/text-animation frame checks. Native security tests used two concurrent disposable workers and actual denied write attempts. See VERIFICATION.md and retained artifact reports.

New/updated source:
- services/api/providers.py and scripts/cli_worker.py: native command detection, supported schema modes, authentication/usage errors, private job state and no silent billing fallback.
- services/api/isolation.py, windows_job.py and scripts/episode_boundary_probe.py: native MXC AppContainer/non-elevation/write-denial verification and controller-bound process trees.
- services/api/file_writer.py: scoped paths, atomic writes, Windows parent handles, link rejection and locks.
- services/api/snapshots.py: immutable complete brand/prompt/template/music pins.
- services/api/core.py, creative.py, main.py, worker.py, media.py: controller-only index, local authoritative state, structured creative orchestration and isolated deterministic media.
- scripts/production_worker.py: fixed reviewed worker entry, not model-generated shell.
- video/remotion/render.mjs: the same composition, local bundles/caches and supported read-only native runtime.
- scripts/setup_media_runtime.py and ffmpeg_compat.cs: explicit development-only runtime preparation; no second renderer.
- apps/dashboard/src/main.tsx: provider selection/test controls, AI progress/cancel/retry, pinned input details and genuine Episode Isolation status.
- .env.example, launcher/setup/verification scripts, AGENTS.md, WORKFLOW.md and all four REEL instructions: updated operational guidance.

Creative files:
1. prompts/00_MASTER_PROMPT.md (v1.1.0).
2. brand/references/ODD_FRAME_OFFICIAL_CONTENT_BIBLE_v1.md.
3. brand/skills/ODD_FRAME_FANBASE_GROWTH_PSYCHOLOGY_SKILL.md.
4. brand/skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md.
5. brand/skills/ODD_FRAME_TYPOGRAPHY_AND_MOTION_GUIDE.md.
6. brand/SKILLS_MANIFEST.json and brand/ODD_FRAME_RULES.json.
7. prompts/01_IDEA_GENERATION.md.
8. prompts/02_SCRIPT_WRITING.md.
9. prompts/03_SCRIPT_REVIEW.md.
10. prompts/04_CHARACTER_BIBLE.md.
11. prompts/05_STORYBOARD.md.
12. prompts/06_FLOW_IMAGE_PROMPTS.md.
13. prompts/07_RETENTION_AUDIT.md.
14. prompts/08_REMOTION_EDIT.md.
15. prompts/09_AUDIO_MIXING.md.
16. prompts/10_QC_AND_EXPORT.md.
17. prompts/11_PUBLISHING.md.

Operating instructions: README.md, AI_PROVIDERS.md, SECURITY.md, WORKFLOW.md, AGENTS.md, workflows/REEL-CREATE.md, REEL-PREPARE.md, REEL-EDIT.md and REEL-EXPORT.md.

First real Reel: Test Codex -> Create New Reel -> select -> review script -> approve once -> automatic preparation -> download Flow image JSON -> generate stills externally -> import stills/narration/phrase SRT/instrumental -> automatic isolated assembly/QC/export. No still motion, character animation, SFX or publishing.

Claude subscription login was detected but is not routed through dashboard automation; no eligible Claude API credential was supplied. Manual Claude export/import remains available. No actual Facebook integration or scientific/artistic/acoustic guarantees are claimed. Signature music is pinned when supplied/configured; no licensed music asset was invented.
