# Authorized isolated export

The frozen script approval authorizes editing/export; no second script approval. Automatic editing stops at a reviewable draft. Render Final Video queues the exact saved editor revision. Missing assets, revoked authorization, stale inputs and technical failures block export. No publishing exists.

The controller queues a local job. A verified non-elevated Windows MXC worker renders the existing pinned composition. Shared code/runtime is read-only; global SQLite and sibling writes are denied. A Job Object terminates descendants if the controller exits. Outputs, bundles, caches and logs stay inside the episode. Unavailable isolation never falls back to unrestricted rendering.

Render a 540x960 review preview and QC it, then a 1080x1920/30 FPS H.264/AAC final. Measured normalization targets -16 LUFS/-1.5 dBTP while preserving frames. Actual FFprobe/full decode checks settings, duration, coverage, true peak/loudness and black intervals. Recheck frozen narration and all original asset hashes before committing a versioned MP4.

Development setup prepares a shared read-only media runtime through Remotion's documented binariesDirectory option for MXC/FFmpeg 9 compatibility; this is not a second renderer. Dependencies are hash-pinned. A changed binary blocks existing episodes rather than silently altering them.

Final files/QC/publishing draft live in 07_export. Editable timeline, captions, two-source mix and props stay in 06_edit. Local job/state/history files are authoritative; the controller derives dashboard/index views. Retry creates a new version without changing story/assets. Interrupted renders resume; interrupted AI requests require explicit retry.

Technical checks do not prove story satisfaction, image fidelity, acoustic accuracy, licensing or real audience retention. Reports separate executed checks from human-benefit checks.
