# ODD FRAME — 10_QC_AND_EXPORT

Version: 1.0.0
Responsibility: QA Agent

This stage requires the mandatory four-document loader and master prompt. Latest ODD_FRAME_RULES.json overrides historical conflicts. Return only the requested format; never claim a failed model call succeeded.

INPUT: frozen approval and export authorization, asset fingerprints, assembled timeline, actual preview and encoded final media. OUTPUT: machine-readable QC plus QC_REPORT.md distinguishing executed checks, blockers, warnings and human-benefit checks.

Fail on revoked/mismatched narration approval, missing/corrupt assets, ungrounded scene boundaries, caption text mismatch, image aspect mismatch, missing font, wrong soundtrack sources, stale asset fingerprints, decode failure or incorrect video settings. Verify scene order and coverage, required captions within safe bounds, no image-motion code path, no AI video inputs or SFX, measured audio levels, no clipping and complete audio/video duration. FFprobe must verify actual h264 1080×1920 30 FPS and AAC; fully decode the output and test for blank frames.

Render a review preview first, validate it, then automatically export final when gates pass under the single script authorization. No second creative approval. Do not publish. Preserve editable Remotion props and manifests, progress, history and failed-job logs. Never label quality perfect based on metadata checks; actual visual storytelling, illustration fidelity, instrumental content and listening benefit from human viewing. Retry is idempotent and must not rewrite scripts or replace approved assets.
