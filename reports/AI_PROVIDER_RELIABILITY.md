# AI provider reliability: OF_R002 forensic investigation and repair

Post-implementation update: the owner subsequently authorized integration, and the reliability fix was merged locally into main as `8470238`. See [the main merge report](AI_PROVIDER_MAIN_MERGE.md). The investigation and pre-merge statements below describe the earlier implementation stage.

Branch: `fix/ai-progress-retry`, worktree `E:/facebook-ai-reliability`, based on production `main` at `4781f23`. Production was inspected read-only. No production job was restarted, no provider credits were consumed, and this branch has not been merged or pushed. The storytelling upgrade is not included.

## Confirmed failure and current episode state

Episode: **OF_R002 — The Stakes in the River**, database episode ID 2.

Failed preparation attempt: `519643a8-a958-43d0-8737-c10da92eacbd`.

| Persisted evidence (UTC) | Observation |
|---|---|
| 2026-11-06 08:53:05.976 | Run created |
| 08:53:06.395 | Four pinned documents/master/stage validation recorded |
| 08:53:06.467 | Complete schema-bound request saved |
| 08:53:07.672 | Controller recorded authentication/isolation stage |
| 08:53:08.802 | Isolated worker started the provider process |
| 08:53:13.656 | Codex emitted `thread.started` |
| 08:53:13.732 | Codex emitted `turn.started` |
| 08:58:09.127 | Attempt failed: `TIMEOUT: Worker timeout after 300s` |

The recorded JSONL contains only the two startup events (101 bytes). Provider stderr is empty. No `response.json` exists. Consequently, this failure was **not a JSON/schema validation or artifact-save failure**: it occurred before final output was available. The immediate cause was the configured hard worker deadline, about 303 seconds after run creation. Authentication/isolation had already passed far enough to launch Codex and establish a provider session; the displayed authentication message was stale.

Why the remote turn did not return within 300 seconds is not established by the retained evidence. A running process and a started turn do not prove healthy remote generation. There is no recorded quota, rate-limit or authentication rejection. Available subscription credit cannot be independently established from these logs.

A later explicit retry, `505a537f-0e92-494d-9dc6-8e6ab5601a08`, **already succeeded**: created 08:59:11.412, process started 08:59:14.884, provider session 08:59:18.177, turn started 08:59:18.635, response activity 09:03:24.667 and successful provider exit 09:03:25.440. Its final JSON is 50,076 bytes, its JSONL is 53,063 bytes, and stderr is empty. Controller validation and artifact persistence followed. Current read-only inspection finds a **20-scene package**, approved narration hash `96df91049edcfa566a1629f89608b53650c96d96e6968e09e7fbc1f95c4478fe`, no current error, and status **ASSETS_BLOCKED**.

**Resume OF_R002 through Asset Manager:** supply/fix the missing or invalid assets reported by its actual checklist, refresh/scan, then continue to editing when validation succeeds. Do not regenerate its successful production package or reapprove/rewrite its narration to repair this historical timeout. No live OF_R002 retry was performed during this task.

## Authentication, invocation and request size

The installed native CLI reports **codex-cli 0.166.0**. A non-generating official `login status` check reports authenticated **ChatGPT login**, eligible for the configured integration. No credential contents were inspected or changed. Production settings inspected read-only are provider `codex_cli`, blank model (installed CLI default), context budget 200,000, application output reserve 12,000 and worker timeout 300 seconds.

The failed request has a conservative context upper bound of 179,895 and a persisted CLI-request file of 179,363 bytes. This is not a measured token count. The application's 12,000 output-token budget is recorded in request/context accounting; it is not a new CLI token-limit flag. No unsupported token-limit option was added. There is no evidence of truncated output on the failed attempt because it returned no final response; the later attempt returned valid complete JSON.

The retained invocation uses the existing private job Codex home and episode working directory, `codex --no-daemon exec --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check --sandbox read-only --output-schema <episode schema> --output-last-message <episode response> --json --color never`, with existing disabled tools/features, approvals and private runtime configuration. Installed `exec --help` confirms `--json`, `--output-schema`, `--output-last-message`, `--ephemeral` and `--sandbox`. Native MXC, Job Objects, read-only credentials, official login and model selection remain unchanged. No bypass flags or new authentication methods were introduced.

Current login eligibility is not proof of historical credit balance, remote health or an exact account/workspace identity. The historical provider startup events are stronger evidence that this attempt reached Codex than a new terminal login probe. No new live generation was needed or run.

## Root causes in the application

1. **Stale controller stage:** `execute_run()` sets authentication/isolation before `providers.generate()`, then waits for the entire call. The CLI worker already consumes JSONL incrementally and writes activity, but Ideas and other REST-driven panels read the unchanged database `stage`. The original live-run panel also displayed static document-loading copy throughout generation.
2. **Hard 300-second limit:** `isolation.launch()` applies a monotonic overall worker deadline and terminates the process tree when it expires. Actual provider activity did not extend it. The failed attempt was silent after its turn-start event.
3. **Collapsed diagnosis:** failure messages lost the failed stage and instructed users to check authentication/usage regardless of evidence. Historical failure state lacked a structured public diagnosis.
4. **Stale episode error:** a new preparation run could be registered without clearing `episode.data.error`. Thus a previous timeout remained visible while its retry ran. Retry registration checked active jobs without a shared scheduling lock, leaving a race between concurrent submissions.

## Repair

### Native events, persistence and live transport

Reuse the existing pipeline: CLI JSONL → isolated worker → bounded episode-local journals → FastAPI `/api/activity` and `/api/activity/stream` → TanStack Query/React. Workers **do not write the shared SQLite index**. Journals retain ordered per-job sequences with stable event IDs and distinct attempt/run IDs; the existing 600-event retention limit and reconnect reset behavior remain. The SSE cursor uses `Last-Event-ID`; subscribing is read-only and never starts a job. No credentials are placed in SSE URLs.

Codex native `thread.started`, `turn.started`, agent-message completion and `turn.completed` are normalized to fixed status messages. `error`/`turn.failed` are categorized without forwarding private error bodies. Claude's existing init/assistant/result adapter remains supported. Internal reasoning, response text, prompts, tool arguments, environment values and credentials are never included in public activity. Unexpected tool use remains rejected.

The worker continues incremental asynchronous stdout consumption, including partial-line assembly. Malformed JSONL lines are ignored safely; structured final output is still required. Individual JSONL lines are bounded, total captured stdout remains capped at 64 MiB, and stderr is drained concurrently with bounded capture. Process exit and cancellation cleanup remain enforced. The complete final response still goes through the controller's schema/coverage validation.

New verified milestones distinguish CLI/authentication checks, isolation checks, process start, complete request delivery to CLI stdin, provider session/turn activity, JSON parsing, schema validation and artifact saving. A stdin handoff is explicitly **not** proof of remote acceptance. The new public attempt projection is reused by runs, episode details and AI Activity; Ideas reads its matching run journal rather than a stale database label.

### Heartbeats, liveness and timeouts

Transport heartbeats and process liveness are separate from provider output. SSE emits a lightweight heartbeat; the header identifies the last transport heartbeat without treating it as generation. The worker checks process liveness every ten seconds and persists `process.alive`, explicitly saying that this is not model progress. Provider-event time is tracked separately and is not advanced by process heartbeats.

The UI shows real milestone timestamps, elapsed time, last provider activity and the last verified process check. Yellow means queued/preflight/unconfirmed handoff; green follows observed request/session/generation/response milestones. Silence produces an honest idle warning, not automatic success, quota diagnosis or an invented percentage.

No timeout was arbitrarily increased or removed. Existing CLI version/auth probes and native preflight retain their bounds; the isolated worker keeps the configured **15–1800 second** limit (production currently 300), now recorded with attempt provenance and shown in the panel. Active events do not silently remove the overall deadline. An owner may choose a larger bounded timeout in Settings for large packages, but this task did not change production settings. Validation and local persistence remain synchronous and do not gain unsafe background cancellation threads; independent deadlines for every local file write are not implemented.

Historical timings before the first persisted event cannot be reconstructed exactly. Future provenance records context-preparation duration; authentication/isolation, startup, native activity, parsing, validation and save event timestamps allow separate observed durations. Sparse provider events cannot reveal hidden model execution phases.

### Errors and retry state

Failures persist a fixed-text public category/message, job/episode/provider, failed stage, timestamp, elapsed time and latest real activity time. A bounded private diagnostic retains the technical error. Categories distinguish authentication, quota, rate limit, unavailable service, network, spawn/exit, timeout, invalid output, artifact persistence, isolation, cancellation and unknown errors. Public APIs no longer expose the raw technical exception as a diagnosis.

Each retry retains a stable `job_group_id`, creates a new run/attempt UUID and increments `attempt_number`, with `retry_of` provenance. An episode scheduling lock covers eligibility and registration. Duplicate active retries are rejected or return the already registered manual attempt. Registration clears the **current** episode error and changes `pending_run`; old records and terminal events remain immutable history. A late older failure cannot overwrite a newer attempt's episode state. Completed production packages cannot be regenerated by retrying an old failure.

If preparation failed after some text/JSON artifacts were written, the next explicit retry archives those existing character/storyboard/Flow artifacts within the new attempt before replacing derived files. Approved narration and episode media are not regenerated or copied. Preparation remains one coherent model call; there is no false claim of independently completed documents while that call runs.

The shadcn activity card shows the episode, provider, job/attempt, true stages, idle state, event history and actionable diagnosis. Prior failed attempts are collapsed separately in AI Activity; current attempt panels ignore older errors. Existing Retry / Resume and AI Activity retry actions remain explicit owner actions. No automatic retry or billing/provider substitution was added.

## Verification results

All mutations and fake subprocesses use disposable `artifacts/*` or pytest temporary roots. The browser QA server uses `artifacts.qa_app`, an explicit deterministic provider adapter; it must not be confused with a live Codex test.

| Check | Result | Evidence |
|---|---|---|
| Existing complete backend suite, first run | 152 PASS, 2 FAIL: old Claude test doubles lacked the new stderr pipe | `artifacts/full-regression.log` |
| Both affected Claude fixtures after correction | PASS: 2 tests | `artifacts/claude-adapter-final.log` |
| Provider security + final reliability integration | PASS: 53 tests | `artifacts/security-reliability-final.log` |
| Expanded reliability suite | PASS: 26 tests | `artifacts/reliability-complete.log` |
| Latest bounded streaming / heartbeat tests | PASS: 10 tests | `artifacts/stream-final.log` |
| Combined reliability suite | PASS: 28 tests | `artifacts/reliability-verified.log` |
| Final completion-label and heartbeat distinction | PASS: 2 tests (one additional distinct case) | `artifacts/final-status.log` |
| Dashboard TypeScript + Vite production build | PASS | `npm run build`, `artifacts/build-verified.log` |
| Frontend unit tests | PASS: 13 tests | `npm run test:ui`, `artifacts/frontend-tests-verified.log` |
| Remotion TypeScript | PASS | `npm run typecheck`, `artifacts/remotion-types-verified.log` |
| Actual browser retry / streaming / refresh / replay | PASS | `node scripts/ai-reliability-qa.mjs`, `artifacts/browser-release.log`, `artifacts/ai-browser/result.json` |
| Live provider generation | NOT RUN | No new provider usage authorized or consumed |

There are 154 existing backend cases and 29 new reliability cases, all passing across the full and focused runs after the fixture correction (183 distinct cases; not a claim of one 183-test invocation). The two initial failures are retained in the report and logs. The existing FastAPI/Starlette httpx test-client deprecation warning remains; no unrelated dependency upgrade was introduced.

The real fake-CLI test splits a JSONL line across writes, emits malformed data and concurrent large stderr, and **blocks process completion until another thread observes the persisted provider-turn event**. This proves worker streaming before subprocess exit. Failure subprocesses cover nonzero exit, quota/rate errors, missing/invalid/truncated final output, overlarge event rejection and interrupted child cleanup. Controller tests cover exact categorized persistence, artifact-save failure, late failures, retry history, duplicate registration, approval preservation and three distinct episode journals. The three-episode test does not claim three live model calls or three simultaneous production renders.

The browser receives an SSE provider event while the attempt is still `RUNNING`; then disconnects, refreshes, observes the same Attempt 2 complete, replays from a real earlier cursor, and finds Attempt 1's timeout in historical details. No job is restarted by refresh. A repeated QA run initially found multiple prior-attempt summaries from different disposable episodes; its locator was narrowed to the exact failed job ID. No application defect or failure was hidden by that harness correction.

Screenshots: [failed attempt](../artifacts/ai-browser/failed.png), [provider running](../artifacts/ai-browser/running.png), [completed retry](../artifacts/ai-browser/complete.png). Disposable QA preview: `http://127.0.0.1:5192`, API `8142`. These ports/data are separate from production; the preview deliberately uses a fake provider. No production services were restarted.

## Files and remaining scope

Backend: `services/api/activity.py`, `job_errors.py`, `creative.py`, `providers.py`, `story_ideas.py`, `main.py`; worker: `scripts/cli_worker.py`. Frontend: `activity.tsx`, `ideas.tsx`, `main.tsx`, new `idea-progress.tsx`, `production-activity.tsx`, `provider-progress.css`, `job-lifecycle.ts` and its test. Tests/QA: `tests/test_ai_reliability.py`, the stderr pipe fixture in `tests/test_provider_security.py`, and `scripts/ai-reliability-qa.mjs`. No dependency/lockfile, database schema, source creative document, approved script, renderer or native isolation change.

Live subscription availability, new live generation quality, external provider reliability and full screen-reader/touch-device behavior remain unverified. The application cannot display internal provider reasoning or invent fine-grained document progress when the native CLI is silent. No generated audio is claimed. Production integration still requires reviewing this focused branch; this task does not merge it or the unrelated storytelling branch.
