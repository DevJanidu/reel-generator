---
name: odd-frame-cinematic-2d-still-art-direction
description: Direct ODD FRAME hand-drawn cinematic 2D story stills during preproduction, visual-bible/storyboard shot authoring, image-prompt regeneration and image-batch review. Applies to new Reels; preserve historical pinned versions.
metadata:
  version: "3.0.0"
  status: ready-for-owner-approval
  applies_to: all-new-odd-frame-reels
  stages: idea-to-preproduction, visual-bible, storyboard, google-flow-image-jobs, image-batch-review
  priority: mandatory-before-image-prompts
---

# ODD FRAME — Cinematic Hand-Drawn 2D Story Still Skill v3.0

Version: 3.0.0
Status: ready-for-owner-approval

## 0. Invocation contract: READ BEFORE WRITING

Trigger: Every ODD FRAME Reel preproduction run, every image-prompt regeneration, and any rewrite of a visual-bible or storyboard image shot. The Reel generator must read the full, current approved version of this skill before composing any image prompt. This is not a passive file that happens to exist in a folder.

### Required execution order

1. Load the approved script, genre, scene intents, and existing approved visual references.
2. Read this complete skill and record the skill's version, path, and checksum in the generation manifest.
3. Build or resolve an episode-specific canonical visual bible covering character designs, relative scale, buildings, props, geography, materials, and lighting rules. Reuse approved definitions; do not silently replace them.
4. Build the story-state ledger (chronological and flashback states, ownership, prop counts, locations, time of day, damage, water/terrain state, emotional change).
5. Plan all shots as one coherent batch, including visual focal point and shot progression.
6. Compile fully self-contained Google Flow image prompts from the approved definitions for only the subjects visible/relevant in each shot.
7. Run deterministic prompt QA on the entire batch, correcting conflicts before export.
8. Export the existing Google Flow JSON v1.0 queue plus a reference manifest and skill/version metadata as nonbreaking sidecars. Verify import compatibility.
9. After images exist, inspect the generated pictures side by side. Reject inconsistent images and regenerate those scenes with the same locked references.

Hard gate: If this skill was not read, references were unresolved for an essential visible subject, or the canonical scene descriptions contradict each other, do not mark the image queue READY. Return actionable BLOCKED or REVIEW information. Do not present prompt compilation as successful visual validation; the image model must still be checked after generation.

## 1. Identity and aim

ODD FRAME creates original, entertainment-first short stories across mystery, comedy, horror, romance, friendship, drama, betrayal, fantasy and adventure. The goal is one believable frame from a professionally illustrated 2D animated story, not an engineering chart, technical cross-section, AI marketing poster, cinematic photograph, anime frame or 3D render.

The most important visual formula is:

Believable, well-drawn story world + clearly staged character action + readable expression + one intentional visual focus + consistent world state.

Study external references for transferable art techniques, not copyrighted characters, exact layouts, imagery, logos or another channel's brand identity. Every final published image must be original to ODD FRAME.

## 2. Style lock — visible in every generated still

- Strictly 2D hand-illustrated artwork for characters, scenery, props, lighting, shadows, and textures.
- Fine, confident dark-brown or charcoal ink contours with organic hand-drawn irregularity. Clear silhouettes and readable shapes.
- Flat base colors plus restrained two-step cel shading, with a little soft painted background variation. Never glossy 3D materials.
- Warm, earthy painted-storybook palette: sand, dusty ochre, muted brown, warm beige, pale ivory, gentle sage, subdued slate-blue. Retain important approved fur, clothing and prop colors.
- Environment detail is deliberate: hand-illustrated wood grain, woven reeds, textured soil, small stones, sparse grasses, soft layered hills, trees and natural wear as appropriate to the setting.
- Simplified expressive faces and gestures that remain understandable on a phone. Animal anatomy and distinctive character identifiers remain stable.
- Foreground / midground / background layers create perspective without fake depth of field or photorealism. Spatial relationships must be believable.
- Natural scene lighting first: warm directional afternoon sunlight for daylight; soft moonlight or practical interior lighting when story-appropriate. Dark mystery lighting is not a default for comedy or daytime scenes.
- Do not use excessive yellow glow, a uniform yellow filter, horror darkness in ordinary scenes, heavy fog, lens flares, excessive particles or washed-out bloom.

### Preferred ODD FRAME brand color responsibilities

| Color | Target | Intended role |
| --- | --- | --- |
| Midnight charcoal | #14171C | Ink contours, deep shadows, dark framing |
| Muted slate | #41464E | Cooler shadows, workwear, weathered secondary surfaces |
| Lifted gray | #7D838B | Secondary readable forms |
| Warm ivory | #F1EBDD | Readable muzzle/face features, small natural highlights |
| Signature golden yellow | #FFD43B | One narratively relevant object / clue / attention zone |
| Pale yellow | #FFF2B0 | Tiny true-light core or highlight |
| Muted ochre | #A98428 | Earth and shadowed gold, restrained reflections |

These are brand targets, not a requirement to recolor every item. Characters retain their approved species-specific colors. Yellow is a deliberate attention tool, not a mandatory glowing halo. A plain yellow survey stake in daylight does not emit light. The correct shot can be bright, friendly or cheerful while remaining distinctly ODD FRAME.

## 3. Signature ground and interior material treatment

For applicable terrestrial scenes, prefer artistically textured earth: warm sandy dirt, large irregular dry-earth plates, thin branching cracks, scattered pebbles and tufts of sparse grass. The cracks must appear naturally part of the environment, not an exaggerated fissure field or diagram grid. A set can also use weathered large granite/stone floor slabs with visible irregular joints, matte texture and hand-drawn edge wear.

The creator's preferred signature treatment may appear indoors if physically established by the location design (for example, a lodge built over exposed packed earth, or a stone-floored chamber). Do not silently transform a river, wooden floor, bedroom or other approved location into desert terrain. The approved visual bible and narration take precedence; preserve flooring continuity once locked. This is a set-material design rule, not an excuse to violate the story's physical geography.

Never replace cracked soil with polished modern ceramic tile or featureless plastic-smooth ground. Do not over-texture the floor so it competes with the characters.

## 4. Canonical visual bible — create once for each Reel

For each visible recurring character, lock an immutable full description containing: species, head and muzzle shape, eyes, ears, teeth, identifying marks, fur/body colors, exact relative head/body proportions, arms/legs, tail shape and pattern, clothing design and colors, allowed accessories, and distinctive gestures. Lock height relationships in shared world space, not screen pixels. Specify clothing alternates only where approved by story state.

For each important building, lock: wall/roof materials, roof pitch/silhouette, overall proportion, exact door side and relative door height, window count/position, repair patches, colors, nearby landmarks and ground elevation. Do not let a view angle redesign architecture.

For each significant prop, lock: size relative to a character, color, material, shape, count, distinguishing markings, and whether it is held, planted, placed, open, damaged or repaired.

For each location, lock: camera-independent spatial map, river/road direction, slope and elevation relationships, path connections, distances and fixed landmark positions. Distinguish fixed world facts from temporary changes such as rising water or broken items.

Approval and provenance: Reuse supplied/canonical reference images when available. Newly proposed design facts may be drafted but must be visibly marked PROPOSED, not misrepresented as approved. Do not silently invent and overwrite approved references.

## 5. Internal precision vs. visible cinematic language

Keep measurements, geographic coordinates, elevations, scene labels, dimension diagrams and validation constraints in structured internal metadata, not in prose likely to be rendered as visible annotations.

Bad for Google Flow: Telephoto cross-section from south, +0.40 m water, marker A 0.80 m above roof; same moment as S001.

Good for Google Flow: A natural eye-level illustrated wide shot. A worried brown beaver looks toward a slender stake planted firmly in the rising hillside. Its yellow band stands visibly above the roofline of her lodge on the lower riverbank. The calm river is still low. Show the lodge, hillside and stake together so the threat is understandable without labels.

Do not leak engineering-language terms such as cross-section, measurement arrow, annotation, marker A, scale drawing, S001, same as previous, survey elevation +0.80, or camera coordinate into public image prompts. Translate internal numerical logic into visually legible real-world relationships without losing the meaning. Survey stakes and other genuine objects remain visible when the story requires them; their labels do not.

## 6. Per-scene shot design

Plan all shots together to avoid 20 disconnected but individually attractive images. The visual sequence must vary meaningfully: establishing world → character decision/reaction → clue/prop detail → changed circumstance → consequence. Do not create filler angles or repeat the same moment unnecessarily.

For every scene, record internally:

- Story beat and what changed since the last chronological beat.
- Exact visible character count, canonical IDs, poses, emotions, and relative positions.
- Locations and important buildings/props actually visible in the frame.
- Moment-specific state: carried objects, repair progress, water level, doors, evidence and time of day.
- One camera shot: wide, medium two-shot, over-the-shoulder, close-up, detail or low/high angle, chosen for storytelling—not technical diagrams.
- Foreground / midground / background objects, scale perspective, focal target and secondary information.
- Lighting source, shadow direction, color accent purpose and background simplicity.
- Mandatory inclusion/framing (if full-body, complete head, feet and tail with a little breathing room; if wide, include necessary buildings/terrain). Never force full-body characters into an intentional close-up.
- Reference images assigned to visible subjects, plus the episode's approved style reference.
- Spatial scale: A character near a door must fit the approved doorway ratio. A character far uphill must be visibly smaller due to depth, not look like a giant towering over a tiny foreground lodge. Narrative camera angle must be physically plausible.

## 7. Self-contained Google Flow image prompt compiler

Independent Google Flow extension jobs have no reliable memory of earlier scenes. Every prompt must stand alone. Construct each from the canonical bible without rewriting the underlying locked descriptions.

Required output order inside each image prompt:

1. Opening art instruction: Create ONE full-bleed vertical 9:16 original cinematic hand-drawn 2D story still. No text.
2. One visible story moment: action and emotion, not a paragraph of story summary.
3. Visible characters: repeat the full exact canonical descriptions of only the visible characters and their expected count. Explicitly exclude extras.
4. Visible recurring buildings/props: repeat their actual approved identity, construction, scale and scene state.
5. World and geography: include necessary spatial relationships in cinematic, nontechnical language. Do not reference previous prompts or scene IDs.
6. Shot composition: what is framed, foreground/midground/background, proportion to doors, focal target, full-body/close-up requirements.
7. Illustration and palette: locked 2D hand-illustrated style, natural environmental texture, character color preservation, intentional limited golden-yellow accent.
8. Motivated light: source and direction, real reflected light only. State when a colored object is not emissive.
9. Visible moment state: story-time water, objects, costume, repairs, expressions, lighting.
10. Exclusions: no text/letters/numbers, labels, arrows, diagrams, comic panels, split screens, decorative borders, blank caption margin, 3D, CGI, photo, anime, anatomy errors, additional characters, watermarks, logos.

Avoid repeated irrelevant prose and descriptions of absent characters; long prompts are justified only by genuinely needed continuity facts. Never truncate a prompt silently to fit a model/extension limit. If a prompt cannot fit, surface a blocker or revise the scene intelligently while retaining essential definitions.

## 8. Aspect ratio, framing and mobile readability

Exactly one image per job, vertical 9:16, full-bleed edge to edge. Target 1080 × 1920 or higher at the same aspect ratio.

No panels, grids, split-screen scenes, blank strips for captions, white margins or decorative cards.

Important faces, gestures and props must read at mobile thumbnail size. Avoid overwhelming detail and distant tiny characters.

Place vital clues away from expected Facebook control/caption overlap zones, but do not draw empty caption boxes or reserve blank bars.

The shot should tell the story with all generated text removed.

## 9. References and visual identity

Assign approved reference images for each visible character and location/structure/prop when the extension genuinely supports them. Output a REFERENCE_MANIFEST.json sidecar listing required and available references per job. No fabricated filenames, fake attachments or assumptions that shared seeds preserve identity.

Existing JSON v1.0 job format remains compatible:

```json
{
  "job_id": "S001_IMG",
  "scene_id": "S001",
  "type": "image",
  "prompt": "Fully self-contained cinematic 2D image prompt ...",
  "source_image": null,
  "output_name": "S001"
}
```

Keep source_image: null when the extension has not actually attached an image. Do not misuse one legacy field to falsely claim multiple references. Enrich reference support through a tested, backward-compatible extension capability or a separate manifest.

## 10. Hard exclusions and failure examples

Reject images containing: displayed technical terms, floating scene labels, numbers or dimension annotations; tutorial arrows; labeled survey diagrams; disconnected world geometry; giant characters beside miniature buildings; inconsistent faces/vests/tails; duplicate animals or extra limbs; roofing patches changing on their own; random glowing props; simultaneous moments/comic panels; sterile or photorealistic materials; text or logos; artwork that reads as a poster instead of a single moment in a story.

Do not make a diagram to explain a physical puzzle. Make the situation legible through a believable camera view and meaningful expression/gesture.

## 11. Batch QA and regeneration gate

Before export, perform automated checks for missing canonical descriptions, visible-character counts, ungrounded new characters, conflicting building facts, wrong prop count, impossible scene state, contradictory water level, absent shot framing, extra panels, annotation-triggering technical terms, unresolved reference assignments, and JSON parser compatibility. Output PASS, REVIEW, or BLOCKED with scene-specific reasons.

After generation, compare all images side by side. Verify facial identity, fur, clothing, tails, buildings, roof repairs, direction of slope and river, stakes/props, time/weather, physical scale and shot variety. Actual visible errors require regeneration of affected stills. A prompt passing lint is not proof the rendered image passed.

## 12. Example: OF_R002 character scene — art-direction test ONLY

Important: The following is a test example, not the global cast or a replacement for OF_R002's approved visual bible. Read the episode's actual approved assets and descriptions before assembling production shots.

Action: Mara discovers a yellow survey stake on the uphill slope and points toward it, distressed. Alder, slightly taller, stays a few steps behind, averts his gaze. The lower-bank wooden lodge and calm river remain visible. Show the spatial relation as one coherent medium-wide storytelling shot.

Illustration: soft late-afternoon left-side sunlight; expressive hand-drawn anthropomorphic beavers with two-step cel shading and dark ink contours; gently detailed weathered timbers, patched woven-reed roof and dry cracked soil. Golden-yellow highlights only on the physical stake band and subtle natural sunlit edges. The stake is a painted object, not a lamp. No cross-sectional cutaways, annotations, labels, technical numbers, caption zones or diagram typography.

Continuity: Use the precise locked Mara/Alder descriptions and lodge/prop geography from this specific episode's approved bible. If these are unavailable, stop and request them instead of inventing new character or building identities.

## 13. Skill installation / acceptance tests

The developer integrating this skill into the Reel generator must:

- Place it with other canonical creative skills in the existing application's approved skill directory; register it in the existing skill loader, not as a new standalone app.
- Enforce the read-before-prompt stage: record skill_version, file checksum, loaded timestamp and applicable visual-bible version in each generation attempt/manifest.
- Ensure prompt generation fails with an actionable error when the skill file is missing/unreadable, rather than silently reverting to old prompt templates.
- Verify the skill is used during both initial preproduction and Regenerate Image Prompts, including retries and background CLI jobs.
- Produce example prompts from mystery, comedy, friendship and OF_R002 to verify different lighting situations; not every image should become dark, golden-glowing, or cracked-ground unless continuity calls for it.
- Verify the image queue still imports in the existing Google Flow extension (schema v1.0) and carries self-contained prompts.
- Test attempts with the skill disabled or wrong version; they must not be represented as new-style production-ready jobs.
- Keep approved scripts and historical episodes pinned and unchanged. Do not merge or deploy automatically without owner approval.

Definition of done: The generator demonstrably reads this skill before writing any new Reel's image prompts; prompts exhibit consistent approved character/building/prop descriptions and natural cinematic 2D language; no technical annotation instructions leak into Flow; the existing JSON extension remains compatible; real generated images are reviewed separately.
