# ODD FRAME Visual Continuity Engine v1

The additional cinematic hand-drawn v3 skill is integrated as a candidate pending owner approval. Its activation, immutable read-before-prompt gate, previews, context-capacity requirement and test results are documented in [CINEMATIC_ART_DIRECTION_V3.md](reports/CINEMATIC_ART_DIRECTION_V3.md). It does not replace the four pinned source documents or silently change historical episodes.

Contract: `ODD_FRAME_VISUAL_CONTINUITY_V1`, `1.0.0`. Flow prompt stage: `2.0.0`.

The existing application remains the production station. Approved narration, complete four-document loading, native worker isolation, status streaming, retries, source uploads, Remotion, caption timing and the two-source audio pipeline retain their existing boundaries. No merge, deployment, publishing or paid generation is part of this upgrade.

## Production pipeline audit

| System | Existing implementation reused |
| --- | --- |
| Master and four complete creative documents | `prompts/00_MASTER_PROMPT.md`, `brand/SKILLS_MANIFEST.json`, `services/api/skills.py`; byte lengths, hashes, versions, source signatures, overrides and context bound remain enforced |
| Eight groups, 24 genres, five ideas | `genres.py`, `story_ideas.py`, `idea_models.py`, `prompts/01_IDEA_GENERATION.md`; independent idea sessions and pinned inputs |
| Writing/review | `creative.py`, `prompts/02_SCRIPT_WRITING.md`, `03_SCRIPT_REVIEW.md`; existing provider routing |
| Approval | `creative.approve/approved`; immutable narration hash and one export authorization |
| Preparation | `Package`, coordinated stages 04/05/06/07/11, `creative.populate`; fixed paths through EpisodeWriter |
| Character Bible and storyboard | Existing Markdown documents and scene fields retained; structured sidecars added |
| Flow compiler | Previously directly interpolated raw beat/location/framing/continuity into prompts. This allowed normalized coordinates, side elevations, scene dependencies and caption-band instructions to reach the image model |
| Flow queue | `Flow`/`Job` models: schema 1.0; image-only jobs with six unchanged fields; batches of ten |
| Episode assets | `05_assets/images`, narration, subtitles, music; immutable `.production/input_snapshot`; local status/history |
| References | No structured approved reference registry or verified multi-attachment integration existed in this checkout. New reference manifest describes requirements, actual availability and missing items |
| Image validation | `media.py`: actual decode and technical checks. It does not establish identity, geography, story correctness or art quality |
| Extension | No extension source/manifest was found in the tracked application. Installed metadata audit examined 46 Chrome and seven Edge extension manifests and default/English locale metadata; none matched Google Flow/Queue Studio automation. Actual importer execution and attachment behavior cannot be verified here. No assumption that source_image accepts multiple inputs |
| Jobs/status | Existing providers, isolated workers, episode journals, SSE, controller authorization and retry history reused |

Audit checkout: main at `6d5afd4`; initial uncommitted content was `feat/`. Separate worktrees were present for shadcn UI redesign, storytelling v3.1, AI reliability and three integration branches. No branch switch, merge or worktree edits were performed. The source changes here are in `E:\facebook` only; existing dashboard components and conventions are reused.

## Data contracts

Executable schemas are in `schemas/visual-bible-v1.schema.json`, `story-state-ledger-v1.schema.json`, and `visual-continuity-v1.schema.json`. Models and validators live in `services/api/continuity.py`. All contracts forbid unknown fields. Arrays of typed key/value records preserve strict CLI-provider schema compatibility; duplicate keys fail validation. Input adapters also accept ordinary maps for development/manual compatibility.

The bible contains narration identity, canonical CHAR/BUILDING/PROP/LOC/STYLE assets, complete reusable visual descriptions, private-to-planning specifications, source provenance, approved/proposed design status, geography, fixed relationships, lighting and references. Exact measurements and coordinate data belong in specifications/geography only. Character descriptions equal the package descriptions verbatim.

The ledger contains fixed properties, a separate initial state for each timeline, and ordered shots. State deltas require the previous value and exact narration evidence, or explicit storyboard evidence for physical staging. Flashbacks use independent chains. Each shot binds its source storyboard revision, visible asset IDs, legacy-to-canonical character assignments, cinematic art direction, scene-specific expressions/lighting, state assertions, optional visible state keys, prop counts and scale checks. Declared height_units are consistent relative episode units, not invented metric dimensions. The trusted controller binds hashes during first import; it does not ask a model to compute them.

Descriptions of incomplete designs are marked proposed with provenance. They are not silently promoted to approved. References have stable IDs, public episode-relative paths, hashes, approval and essential status. Missing essential references block export; optional missing references warn. Existing approved references are reused from the saved bible, not regenerated to match a bad image. Automatic reference creation or approval is not claimed.

## Compilation and validation

Compilation is deterministic and has no provider calls or file writes. It processes only the saved episode plan. It injects complete descriptions only for selected assets, the visible cast/count, one cinematic moment, framing, geography, current visible state, scale composition and episode lighting. Internal specification maps, IDs, raw continuity prose, coordinate tables, measurements and change evidence are never interpolated. All prompts receive Midnight Gold 2D art direction and full image restrictions.

Ambiguous technical conversion is an authoring problem: the provider returns an explicit cinematic layer alongside the internal data under the complete pinned creative instructions. The compiler does not strip measurements from raw prose and guess the remaining physical meaning. Legacy raw prompts with detected leakage are blocked with a diagnostic rather than weakened.

Deterministic checks cover narration identity/coverage, storyboard sequence/revision binding, duplicate IDs/keys, undefined assets/references, exact character equality/count/mapping, opposite geographic relations, timeline existence, prior-state/evidence/fixed-property transitions, declared prop inventory, character/door proportions, perspective planes, consistent scale values across shots, relative heights, missing framing, placeholders and technical leakage. Reference availability requires an approved digest match and actual static-image decoding through scoped paths. Source-image remains null and attachment claims remain false.

Every prompt reports character count, UTF-8 byte length and SHA-256. The compiler blocks above 24,000 UTF-8 bytes instead of truncating. The provider's existing output/context limits still apply. The saved bible/ledger act as the per-episode cache; individual regeneration uses exactly that data without creative calls.

PASS means the implemented text/data checks passed. WARNING retains actionable proposed-design/reference findings. BLOCKED produces no Flow queue. None of these statuses establishes actual generated-image fidelity. Natural-language scene meaning, arbitrary scale/geography contradictions, unsupported narration implications and unstructured object descriptions still need semantic/image review. Deterministic checks apply to declared structured data, not every possible contradiction in prose.

## Existing dashboard and review

Google Flow Prompts now contains Visual Bible/references, scene continuity/export readiness, and batch review in storyboard order using existing shadcn components. Imported images can be compared together and opened at full size. The owner may record pass/warning/reject; each record is explicitly owner-attested and binds the actual decoded image bytes by hash. Replacing the image marks the earlier record stale. No image-analysis model is configured or silently invoked.

For declared reference slots the owner can optionally select an imported image and Pin approved reference. The controller decodes it and copies the exact bytes to a unique episode-local reference file, then records its hash in `02_characters/APPROVED_REFERENCES.json`, bound to the canonical plan. This never rewrites the Visual Bible, changes identity or silently replaces a pinned reference. Later source-image changes leave the approved copy intact. Existing direct bible references remain supported. A reference pin is an optional owner action, not another mandatory production approval.

Prepare scene regeneration validates the complete saved plan and writes a unique single-scene Flow 1.0 queue plus sidecar. It does not call Google Flow, replace an image, rewrite identity, change narration or allocate another episode. Historical packages without a structured plan require an explicit separate versioned migration. No historical adoption/repinning occurs automatically.

## Artifacts and compatibility

New episodes snapshot stage 2.0.0 and require visual_continuity during preparation. Historical snapshots keep their creative versions; unsafe legacy external prompts still fail the final safety lint. There are no silent historical regenerations. New sidecars:

- `02_characters/VISUAL_BIBLE.json`
- `03_storyboard/STORY_STATE_LEDGER.json`
- `04_google_flow/REFERENCE_MANIFEST.json`
- `reports/CONTINUITY_VALIDATION.json`
- `reports/VISUAL_BATCH_REVIEW.json` when an owner records a review
- `04_google_flow/regenerations/<scene>-<unique-id>.json` and manifest when requested

The Flow JSON remains exactly schema_version, episode_id, jobs. Jobs remain job_id, scene_id, type, prompt, source_image, output_name. Extra metadata is sidecar-only. Queue-schema and field equality tests verify the known importer contract; actual extension import is unverified because its implementation is unavailable. To add attachment support later, first inspect the installed extension, negotiate an optional capability, attach real approved files per job and record delivery receipts. Retain v1 queue import when the capability is absent; never overload source_image with an array.

## OF_R002 regression and boundaries

`scripts/continuity_regression.py` is an explicit development-only, no-provider regression. It verifies the complete historical pinned inputs via snapshots/skills/model_request and writes a new disposable artifacts directory. It never modifies episode files, original images, narration, approvals or snapshots. All 20 scenes are compiled with exact original character descriptions, lower/upper lodge relationship, fixed equal-elevation stake contour, memory/present separation, repairs, low water until dusk, belongings and empty bed. S002 shows the whole lodge and complete planted stake, its actual higher landscape position, believable character scale and low river. No generated annotations, arrows, numeric coordinates or technical elevations appear in positive art direction.

The historical source defines yellow stakes, not an approved separate indicator band or exact metric elevations. This regression preserves that evidence rather than inventing them. Detailed exterior dimensions/windows/rear construction are not fully approved in the source: consistent added architecture is proposed and flagged. No approved reference attachment was found in the structured source. The result is WARNING, suitable for review, not a claim of approved visual fidelity.

Additional synthetic multi-scene tests cover missing-key mystery, mistaken-bag comedy, fox/gem betrayal, repeated-meeting romance, home-hatch horror and travel adventure. They exercise state chains, independent descriptions and absence of river/stake/lodge contamination. They are compiler tests, not real generated art or story-quality evaluations.

## Verification

See `reports/VISUAL_CONTINUITY_IMPLEMENTATION.md` for executed checks, artifact locations, changed files and remaining limits. No real provider or paid image-generation test was run.
