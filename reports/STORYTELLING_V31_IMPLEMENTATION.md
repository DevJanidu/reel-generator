# Combined storytelling intelligence — implementation and verification

Development branch: `feat/storytelling-intelligence-v31` in `E:/facebook-storytelling-v31`, based on production `4781f23aa6045824dddcb80f760c05d89f61fd8f`. Production remains unchanged. This branch has not been merged or pushed.

Core/framework commit: `64aa3e0` (`feat: pin retention-first storytelling with optional Human Mirror analysis`). The following UI/tests/evidence commit contains this report; inspect `git log -2` for the final review tip.

## What existed and what changed

The existing system already had mandatory complete-document reads, a strong entertainment-first master, genre taxonomy, five-idea sessions, internal script review, a ten-item package retention rubric and one immutable script approval. Human Mirror v2.1 was **not fully implemented**: related creative principles existed, but its structured analysis, modes, preference and downstream provenance did not. See [the preimplementation audit](STORYTELLING_V31_AUDIT.md).

Both complete owner specifications are preserved byte-for-byte under `source_documents/storytelling/`. Their hashes, the four unchanged original creative documents and production preservation evidence are recorded in [provenance](STORYTELLING_V31_PROVENANCE.json). Previous prompts, rules and manifest are archived in `source_documents/storytelling/pre_v31/`.

One registered extension combines `ODD_FRAME_RETENTION_FIRST_V1` as the primary framework with optional `ODD_FRAME_HUMAN_MIRROR_V1`. Master/stage prompts are version 3.1.0; production overrides are version 1.3.0. Every new creative request still reads all four complete original documents, plus its complete pinned master/stage, taxonomy, extension and policy. Hash/length/version checks and context-capacity rejection remain active. The illustrative empty-input writing request has a conservative context upper bound of 164,911, including output reserve; actual requests calculate their own bound. See [request receipt](STORYTELLING_V31_CONTEXT_RECEIPT.json).

New ideas receive premise-led `natural`, `subtle` or `none` analysis and concise hook/conflict/development/payoff planning. None is fully valid and cannot carry a fabricated parallel. The existing eight category groups and 24 genre IDs remain unchanged. New sessions offer Automatic, Encourage when natural and Pure entertainment; preferences persist with the session and cannot silently change earlier batches. Explicit legacy ten-idea requests retain their old count/contract.

Writer and reviewer return structured hook, early stakes, conflict, progression, discovery/turning point where appropriate, promise, payoff, ending, plot-thread handling and all ten physical/continuity domains. Editorial observations are not machine proof. Story rhythms and endings remain genre-specific; there is no compulsory discovery, moral, motivational conclusion, twist or happy ending.

The 40–55-second pilot preference is **soft**. No default speaking rate or word budget is invented. An optional owner-supplied measured voice sample enables an explicitly provisional estimate; supplied narration and SRT remain final timing authority. The 12–18-still range for a typical 45–55-second story is planning guidance, never a quota or export limit.

Script Studio and Episode Workspace display a shadcn Retention Audit. Narration hashes identify whether its notes still match the reviewed wording. Owner edits make notes stale immediately, after Save Edits and after refresh. The existing single approval freezes exact wording and snapshots editorial context, including any stale-review warning; it does not silently claim the edited wording was reviewed. Approved context reaches character/storyboard/Flow/publishing requests, an episode audit report, timeline metadata and the official Remotion Studio manifest. It never appends scenes, captions or audio sources.

Optional analytics observations now validate finite numbers, dates and source definitions. Future new-version requests can use recent explicitly recorded observations cautiously. No completion rate is derived from average watch/runtime, no views are relabeled unique viewers, and no causal or viral probability is manufactured. The owner's first-Reel figures remain explicitly owner-reported, unverified small-sample context. Synthetic test observations exist only in disposable test databases.

## Compatibility and scope

Historical snapshots without the extension remain accepted and keep their pinned prompts. New episodes snapshot the new global inputs. Approved narration, episode files, original illustrations, narration audio, SRT, music, exports, authentication, provider execution, isolation, worker limits and rendering infrastructure were not rewritten. No dependency or lockfile changes, database migration or additional approval gate were introduced. The approved neutral shadcn UI and its scroll architecture remain in place.

Backend changes are additive optional metadata, new-version response validation, immutable input snapshot registration, audit freshness and metrics validation. Existing routes are retained. Extended metrics now require observation dates and definitions; ordinary legacy metrics retain their existing period/source requirements.

## Verification

| Check | Result | Evidence |
|---|---|---|
| Read-only baseline checks | PASS: 56 passed, 1 deselected | `artifacts/storytelling-audit/baseline-tests.log` |
| New combined contract tests | PASS: 40 passed | `artifacts/storytelling-tests/combined-tests.log` |
| Added timeline / official Studio metadata test | PASS: 1 passed | `artifacts/storytelling-tests/metadata-retry.log` |
| Complete backend suite | PASS: 194 passed in 1066.80s; the subsequently added metadata test passed separately (195 distinct tests total) | `artifacts/storytelling-tests/full-regression.log`, `metadata-retry.log` |
| Dashboard TypeScript and Vite production build | PASS | `npm run build`; `artifacts/storytelling-tests/build-final.log` |
| Frontend unit tests | PASS: 12 passed | `npm run test:ui`; `artifacts/storytelling-tests/ui-tests-final.log` |
| Remotion TypeScript | PASS | `npm run typecheck`; `artifacts/storytelling-tests/remotion-types.log` |
| Real disposable API + browser workflow | PASS | `node scripts/storytelling-qa.mjs`; `artifacts/storytelling-browser/result.json` |
| Responsive new audit interface | PASS at 1920, 1440, 1366, 1024 and 390 widths | Same browser result, screenshots below |
| Original production safety | PASS: HEAD and `?? feat/` unchanged; 172 public and 29 pinned files, episode statuses/approval hashes/export records unchanged | `STORYTELLING_V31_PROVENANCE.json`, read-only SQLite checks |
| Live Codex / Claude generation | NOT TESTED | No paid or live CLI request executed |
| Audience retention or measured sample-script duration | NOT TESTED | No audience experiment or sample voice recording supplied |

Browser checks use the real disposable backend, static authored fixtures and manual import. They verify eight groups/24 genres, pinned complete-document requests, preference/calibration persistence, five concepts, script/review imports, audit visibility, stale notes after editing/save/refresh, one approval and locked wording. The same comedy genre is tested with none and subtle modes, including the expandable Human World Connection. No browser JavaScript errors or document horizontal overflow were observed at the five widths. Viewport tests establish reachability and layout behavior, not exhaustive touch-device or screen-reader certification.

Early test attempts are retained rather than hidden: two legacy assertions expected the old master version and were updated to 3.1; the first new Studio metadata fixture lacked prepared audio and was corrected to use the actual draft helper; browser harness retries corrected a literal text locator, asynchronous import-clearing race and a Vite hot-reload interruption during concurrent formatting. Final results are listed above. The existing FastAPI/Starlette httpx test-client deprecation warning remains; no dependency upgrade was bundled.

## Editorial verification

[Editorial review and six full scripts](STORYTELLING_V31_EDITORIAL_REVIEW.md) contains 24 distinct reviewed genre premises and full mystery, comedy, horror, betrayal, romance and fantasy samples, with hooks, causal progression, endings, structural before/after comparisons and explicit unresolved production checks. These are agent-authored examples after complete document loading, **not live Codex/Claude outputs**. Mechanical schema/request tests are separate from subjective editorial assessment. No sample is approved or inserted into historical episodes. The review does not prove originality, emotional response, physical staging or retention.

## Preview and evidence

Isolated preview: `http://127.0.0.1:5190`, disposable API port `8140`, manual provider. Data lives only under `artifacts/preview-data`. It contains QA stories, not a copy of production media or credentials. The normal original application remains available separately. Start the same safe preview with `node artifacts/integration/preview.mjs` when its ports are free; the generated runner is local, ignored development evidence.

- [Desktop audit screenshot](../artifacts/storytelling-browser/audit-1440.png)
- [Meaningful connection screenshot](../artifacts/storytelling-browser/meaningful-connection.png)
- [Mobile viewport screenshot](../artifacts/storytelling-browser/script-390.png)
- [Browser results](../artifacts/storytelling-browser/result.json)

Nested app scroll containers mean a full-page screenshot captures the current viewport rather than every panel; desktop audit/component captures supplement viewport images. The oversized mobile component capture is not used as proof that the whole panel is simultaneously visible.

## Adoption and recovery

Review this feature branch before integration; no automatic merge is performed. If adopted, use normal Git integration and the application's established startup process. Future new sessions/episodes pin the new framework; existing sessions and approved episodes keep their immutable source versions. Do not repin historical episodes to activate this upgrade.

To stop using the framework for future creation after adoption, revert the complete source upgrade through reviewed Git commits; do not edit existing episode snapshots or roll back SQLite/media. Keep this branch and archived source versions so episodes created under 3.1 remain inspectable. Previously generated/approved artifacts stay authoritative. Live-provider consistency and actual audience response need a separate explicitly authorized evaluation before claiming creative performance improvements.
