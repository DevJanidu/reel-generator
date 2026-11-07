# Visual continuity implementation and compatibility report

Date: 2026-11-06. Existing station: E:\facebook. No merge, deployment, publishing, dependency installation or live model generation.

## Result

The global preparation path now supports ODD_FRAME_VISUAL_CONTINUITY_V1. New episode snapshots pin Flow prompt stage 2.0.0 and require its canonical bible and ledger. Internal measurements, coordinates, identifiers, evidence and structural data are separated from the explicit cinematic art-direction layer. Legacy unsafe raw prompts fail closed rather than being silently stripped of physical meaning.

The deterministic compiler injects exact canonical descriptions for selected assets, visible cast/count, expression/pose, shot lighting, composition, relevant geography, story state, inventory, scale and Midnight Gold 2D restrictions. It validates structured continuity, source binding and final positive prompt language before emitting an unchanged Flow 1.0 queue. Full details and schema design are in [VISUAL_CONTINUITY.md](../VISUAL_CONTINUITY.md).

The existing Google Flow Prompts page includes Visual Bible, references, scene validation and batch comparison. Owner review records bind image hashes and become stale after image replacement. Approved reference copies are independently pinned and reusable. Individual regeneration reuses the exact saved plan and prepares a unique queue; it does not invoke Flow or rewrite identity.

## Audit and preserved state

Initial checkout was main at 6d5afd4, with only pre-existing untracked feat/ content. Existing branches/worktrees for shadcn UI, storytelling, reliability and integrations were inspected and left untouched. There was no automatic merge or branch switch.

The four source documents, archived copies, master, historical immutable snapshots, approved scripts, production images, current episode status, original queues and current manifests were preserved. Existing provider routing/authentication, native isolation, controller capability checks, cross-process locking, scoped writer, local job history, SSE, Remotion, ElevenLabs import path, captions and two-source audio were reused. No global database writes were added to workers.

## OF_R002 disposable regression

Final output: `artifacts/visual-continuity/OF_R002-2026-11-06T103542.609095_0000/`.

- IMAGE_JOBS.json: 20 image jobs, schema 1.0, unchanged six job fields, source_image null.
- IMAGE_PROMPTS.md and two ten-job batch files.
- VISUAL_BIBLE.json, STORY_STATE_LEDGER.json, REFERENCE_MANIFEST.json, CONTINUITY_VALIDATION.json, PACKAGE.json, PROVENANCE.json and COMPARISON.json.
- Prompts: 2,706–5,535 characters; S002: 4,862 characters; no truncation.
- Original prompt positive-language lint: 11 scenes flagged. Revised batch: zero scenes flagged. This is a text comparison, not an image comparison.
- Exact Mara/Alder descriptions copied unchanged; their relative heights are fixed in episode-relative units. The lower lodge, dry upstream lodge, equal-elevation stake contour, repairs, independent memory timeline, door changes, retrieved belongings, dusk water and empty bed are tracked.
- S002 describes a cinematic wide view containing the whole lodge and entire physically planted stake, truthful height relationship, readable alarm and low river. It contains no technical elevation, scene identifier, coordinates, measurement annotations or diagram instructions in positive art direction.

Overall status is WARNING: 80 missing-reference findings across scene requirements and two proposed building-design findings. The historical package has no approved structured reference assignments, no numeric elevations and incomplete approved exterior architecture. Missing details are not falsely described as approved. It defines yellow stakes, not an approved separate indicator band. Production files were not overwritten and the episode was not repinned.

## Additional genres

Synthetic multiscene cases cover rabbit/missing key mystery; otter/hedgehog exchange of identical bags, ownership and return; fox/valuable object betrayal; two deer meeting repeatedly at a fixed garden gate; badger discovering a hatch beneath its home; and squirrel travel through clearing, ridge and valley. Tests verify scene-local asset injection, identity/count mapping, state progression and rejection of a bible from another narration. These are test fixtures, not generated production stories or visual-quality evidence.

## Executed validation

| Check | Outcome |
| --- | --- |
| Final continuity suite | 48 passed in 22.75 seconds; `artifacts/continuity-final-confirmation.log` |
| Continuity + concurrent commit + approval/export integration checkpoint | 50 passed; `artifacts/continuity-final-04.log` |
| Final approved-reference tamper and standalone-prompt recheck | 2 passed; approved pins cannot silently degrade to optional warnings |
| Broad backend run | 227 passed, 2 failed in 28m13s; `artifacts/continuity-full-01.log`. This run started during implementation. The cast-name failure was corrected and its exact approval/export test subsequently passed; the other failure is the native Studio boundary described below |
| Frontend Vitest | 4 files, 13 tests passed (`npm run test:ui`) |
| Dashboard TypeScript + production build | Passed (`npm run build`) |
| Remotion TypeScript | Passed (`npm run typecheck`) |
| Native official Studio host recheck | 1 passed in 188.99 seconds, with existing native MXC verification and real loopback readiness; no weaker fallback |
| Browser integration | Passed on desktop/mobile: canonical bible, pinned reference selection, ordered thumbnails, owner rejection persistence, pinned-plan regeneration download, no page errors or horizontal overflow; `artifacts/continuity-browser-1793961029980/` |
| JSON contracts | All three exported schema files exactly match implemented models; final canonical plan/Flow JSON round-trips validate; exact v1 top-level/job fields tested |
| OF_R002 | All 20 scenes compiled; exact visible character descriptions; no revised positive-language lint findings; original production files retained |
| Diff whitespace | Passed with CRLF-aware `git -c core.whitespace=cr-at-eol diff --check`; original source line endings retained |

The broad run's native Studio startup failed with `native MXC is unavailable on this executor`, before Studio launch. The separate host-authorized rerun passed without changing or bypassing enforcement. Both failed checks from that broad run passed on recheck; the full suite was not rerun again after the fixes. The initial default pytest temp location was inaccessible; disposable test roots were moved under artifacts. Existing Starlette/httpx deprecation warnings remain; no dependencies were changed. Logs remain in artifacts/ and no test uses paid generation.

## Changed files

| File | Purpose |
| --- | --- |
| services/api/continuity.py | Versioned models, strict-schema-compatible typed records, source binding, compiler, state/reference/scale/geography checks, lint and legacy guard |
| services/api/models.py | Optional versioned Package extension for historical compatibility |
| services/api/creative.py | New-snapshot requirement, trusted hash binding, pre-export compilation and sidecar persistence |
| services/api/main.py | Episode continuity/review detail, owner review records, pinned reference copy and single-scene regeneration endpoints |
| prompts/06_FLOW_IMAGE_PROMPTS.md | Stage 2.0.0 structured cinematic/internal separation instructions |
| scripts/write_stage_prompts.py | Prevent legacy prompt resource regeneration from downgrading stage 2.0.0 |
| apps/dashboard/src/continuity.tsx | Existing-dashboard continuity, reference and review controls using shadcn |
| apps/dashboard/src/main.tsx | Mount continuity controls on existing Flow page |
| schemas/visual-bible-v1.schema.json | Canonical bible JSON Schema |
| schemas/story-state-ledger-v1.schema.json | Ledger JSON Schema |
| schemas/visual-continuity-v1.schema.json | Combined JSON Schema |
| scripts/continuity_regression.py | Explicit read-only historical input migration into disposable versioned artifacts |
| scripts/continuity-ui-qa.mjs | Disposable manual-provider browser integration QA |
| tests/continuity_fixtures.py | Complete structured synthetic package fixture |
| tests/fixtures.py | Existing integration fixture now includes the new contract |
| tests/test_continuity.py | Compiler, schema, six-genre, historical, reference, review and regeneration tests |
| VISUAL_CONTINUITY.md | Global specification, audit, operation and compatibility |
| reports/VISUAL_CONTINUITY_IMPLEMENTATION.md | This report |

## Limits and operation

No matching extension was found in the repository or audited installed Chrome/Edge extension metadata. Known queue fields validate against the existing Flow model; actual extension import and per-job attachments are UNVERIFIED. Reference requirements are sidecar-only and attached remains false. A future optional attachment upgrade must inspect the actual extension and preserve fallback import behavior.

Text validation checks declared structured facts and likely prompt leakage. It cannot guarantee natural-language semantic accuracy or generated-image consistency. Semantic-model validation and generated-image analysis are NOT_PERFORMED; manual batch review remains available. No regenerated artwork, artistic pass, acoustic sync, licensing result or analytics claim is made.

The running production service was not restarted during this source upgrade. Restart the local station when existing work permits to load the updated backend. Historical versions retain their pinned creative inputs; the disposable OF_R002 revision is not silently adopted. No additional mandatory approval was inserted into the normal workflow.
