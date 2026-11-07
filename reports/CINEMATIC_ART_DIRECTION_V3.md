# Cinematic hand-drawn 2D art direction v3.0.0

Status: **ready for owner approval; global activation remains unset**.

The full supplied skill is installed at `brand/skills/odd-frame-cinematic-2d-still-art-direction/SKILL.md`, with its compiler profile in `ART_DIRECTION.json`. The original four mandatory documents and their preserved uploads were not changed. Existing continuity-engine and dashboard work was retained. Nothing was merged, deployed or silently adopted by historical episodes.

## Registration and approval

`brand/SKILLS_MANIFEST.json` registers this as an additional visual skill, separately from the four-document contract. Its candidate record pins the complete 19,302-byte skill and the 2,411-byte profile by SHA-256. `approved` is null and `required` is false while the owner's supplied `ready-for-owner-approval` status is retained. Pending installation does not label old-style output as v3 or interrupt existing pinned workflows.

The owner/development activation command is `python scripts/approve_art_direction.py --approve`, using the station's Python environment. It must be run only after explicit owner approval. Without that flag the script only validates and displays candidate metadata. Activation records an approval receipt for these exact checksums and makes the skill mandatory for subsequent snapshots; it never edits existing snapshots. The source proposal label is retained as provenance; the separate checksum-bound manifest receipt is authoritative after approval. Episode-mode processes cannot run the activation function.

Candidate skill SHA-256: `4295cff8a0abe6daecccdbe14bae735c48e02db8160bfc4e68dbeb4ed5e8f619`.

Compiler profile SHA-256: `7dc73e301a19728db07676c92fde1222af948574104622df11ea57f095afa93d`.

## Enforced invocation

Once approved, `services/api/skills.py` reads and validates the entire pinned skill, source signature, version, length and checksum, plus its compiler profile. It inserts the complete skill into model requests alongside all four complete existing documents, master, production overrides and stage instructions. This is actual request-content delivery and filesystem-read evidence; it does not claim to measure a model's internal attention or artistic compliance.

New episode snapshots include the full skill and profile as immutable hashed files. Initial preparation, manual import validation, asynchronous provider delivery, explicit retries and image-prompt regeneration use the pinned approval. Compilation rereads it independently; no caller-supplied claim that it was read substitutes for loading it. Missing, unreadable, truncated, wrong-version, disabled or changed inputs block instead of reverting to the old style. Missing episode provenance also blocks an attempted fallback. Historical episodes without this approved supplemental skill retain their original art direction.

Every v3 queue gains `04_google_flow/GENERATION_MANIFEST.json`; existing reference and validation sidecars also carry skill identity, version, canonical path, full-read timestamp, byte length, checksum and approval evidence. The generation manifest additionally records the applicable Visual Bible version/hash, plan hash, prompt lengths/hashes, shot progression and text-validation state. Single-scene regeneration writes the same evidence into its unique regeneration manifest with a fresh read timestamp.

## Cinematic compiler changes

V3 prompts follow the supplied order: full-bleed portrait opening; one action/expression; exact visible cast/count; complete relevant canonical assets; truthful geography; composition, scale and focal target; hand-drawn illustration/palette; motivated scene light; current state; exclusions.

Charcoal now serves outlines, shadows and framing rather than being forced to dominate every environment. The profile supports earthy storybook colors, organic ink, two-step cel shading, subtle painted scenery and bright genre-appropriate scenes. Approved fur, costumes, props, architecture, lighting, terrain and floors take precedence. Floor texture comes from the established location, rather than a global cracked-ground instruction. Yellow remains a physical attention cue, not an automatic light source.

The compiler still checks exact character descriptions, visible counts, prop inventory, source storyboard binding, geographic relations, scale, state transitions, framing, placeholders and technical leakage. Final checks now also cover split-screen/comic layouts and the profile's own positive art language. Internal measurements, scene identifiers and planning evidence remain outside image-generation prose.

V3 text QA returns PASS, REVIEW or BLOCKED. Missing essential references and contradictions produce no queue. Proposed designs/optional missing references produce REVIEW. Even PASS is recorded as PROMPT_VALIDATED with visual validation NOT_PERFORMED, never as a claim that generated images passed. The existing batch-review and immutable-reference workflow remains available.

## Context capacity

The measured complete synthetic preparation request needs a conservative context bound of **200,415**, including the existing output reserve. The current production default is 200,000, so that request is correctly blocked at the unchanged guard. Larger real stories may need more. The acceptance fixture explicitly configured 250,000 in disposable settings; the owner's provider, model, budget, authentication and billing were not changed. Select an appropriately supported larger configured context capacity before using v3 for full preparation.

JSON transport is compacted and display-only schema titles are removed from v3 preparation schemas. Property names, validation constraints, full source documents and stage content are preserved. A regression test specifically protects real fields named `title`. No instructions are summarized or silently truncated.

## Review previews

Review directory: `artifacts/art-direction-v3-review-2026-11-06T111740.061000_0000/`.

| Case | Scenes | Text QA | Lighting/material check |
| --- | --- | --- | --- |
| Mystery | 3 | PASS | Soft moonlight, readable faces |
| Comedy | 3 | PASS | Bright restrained afternoon light; two animals and bag ownership |
| Friendship | 3 | PASS | Warm afternoon light, established timber boardwalk preserved |
| OF_R002 | 20 | REVIEW | Established overcast/daylight/dusk chronology and canonical descriptions retained |

Each case contains IMAGE_JOBS.json, IMAGE_PROMPTS.md, REFERENCE_MANIFEST.json, GENERATION_MANIFEST.json and TEST_ONLY.json. The top-level PREVIEW_MANIFEST.json makes clear that approval inside these fixtures is synthetic test approval, **not global owner approval**. OF_R002's proposed architecture and missing approved references remain flagged. The skill's example action, stake band and cracked-soil suggestion were not substituted for its actual source bible/storyboard. Original episode files, narration and images were not overwritten.

These are deterministic test prompts. No model-generated artwork or visual-consistency pass is claimed.

## Verification

- Combined new-skill and continuity release check: **68 passed** (`artifacts/art-direction-v3-release-check.log`).
- Additional final QA cases for panel layout and profile-language leakage: **2 passed**. Together these cover the 22 new art-direction cases and 48 existing continuity cases.
- Pipeline compatibility checkpoint: **52 passed**, including complete four-document/source preservation, coordinated provider request delivery, existing approval/export and context failure (`artifacts/art-direction-compatibility-tests.log`).
- Asynchronous CLI-boundary delivery and explicit retry are tested with a mocked provider; no real CLI generation or paid model call ran.
- Frontend: **13 tests passed**; dashboard TypeScript/production build passed.
- `node scripts/validate_art_direction_skill.mjs`: YAML, supported frontmatter, name, metadata, all 14 complete sections, scaffold and checksum checks passed. The bundled Python skill validator was attempted but cannot run because PyYAML is absent; the already installed js-yaml parser was used without installing dependencies.
- Known Google Flow schema 1.0 parses with exactly the unchanged top-level and six job fields, all image jobs and source_image null.
- CRLF-aware diff whitespace check passed. Existing Starlette/httpx deprecation warnings remain.

Actual import into the Google Flow extension was not executed, and reference attachment capability remains unverified. The legacy queue shape was preserved; references and skill metadata remain sidecars. Actual generated images still require separate side-by-side inspection.

## Files changed for this skill integration

- `brand/skills/odd-frame-cinematic-2d-still-art-direction/SKILL.md`
- `brand/skills/odd-frame-cinematic-2d-still-art-direction/ART_DIRECTION.json`
- `brand/SKILLS_MANIFEST.json`
- `services/api/skills.py`
- `services/api/snapshots.py`
- `services/api/creative.py`
- `services/api/continuity.py`
- `services/api/main.py`
- `scripts/approve_art_direction.py`
- `scripts/validate_art_direction_skill.mjs`
- `tests/test_art_direction_v3.py`
- `tests/conftest.py` (explicit synthetic capacity only)
- `VISUAL_CONTINUITY.md`
- `reports/CINEMATIC_ART_DIRECTION_V3.md`

The earlier continuity-engine files already present in the working tree remain unmerged and preserved. No runtime restart or production activation was performed.
