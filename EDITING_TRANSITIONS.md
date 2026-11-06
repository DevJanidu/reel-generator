# ODD FRAME editing rules — Cinematic Transitions v1

Profile `ODD_FRAME_CINEMATIC_TRANSITIONS_V1` · version 1.0.0 · rules override version 1.2.0 · default for NEW episodes.
Classic v1.0 and Cinematic Flow v1.1 stay available; existing episodes keep their pinned profile unless the owner explicitly
migrates one (Edit Studio → *Adopt Cinematic Transitions v1 and rebuild*). OF_R001 was migrated with the owner's authorization.

Stills never move (no zoom, pan, Ken Burns, parallax). Transitions are silent. Exactly narration + the signature instrumental.

## The five transitions (30 fps)

| Name | Frames | Use for | Avoid |
|---|---|---|---|
| `hard_cut` (default) | 0 | hooks, discoveries, reactions, changes of action, important beats, suspense, reveals, fast progression | — |
| `graphic_match_cut` | 0 | two neighbouring stills that deliberately correspond (shape, position, framing) | claiming a match nobody verified in the artwork |
| `short_crossfade` | 7 (5–8) | gentle emotional continuity, quiet moments, friendship, sadness, romance, subtle atmosphere | overlapping silhouettes / confusing double exposure |
| `emotional_crossfade` | 11 (9–12) | sparingly: emotional pauses, memories, reflection, gentle resolutions | fast suspense or action |
| `dip_to_charcoal` | 12 (10–14), `#14171C` | meaningful time jumps, major location or chapter changes, dramatic separations | ordinary scene changes |

Loose guide only: about 65% hard or graphic match cuts, 25% short crossfades, 10% dips or emotional crossfades. These are not
quotas. Narrative suitability wins: a tense mystery may be almost all hard cuts.

## Who decides

There is one validated decision per scene boundary. When more than one source exists, the first in this list is used:

1. The owner's overrides (`PUT /api/episodes/{id}/transitions`).
2. `06_edit/transition_decisions.json`, the editorial plan. It uses a strict schema:
   `from_scene`, `to_scene`, `transition`, `duration_frames`, `narrative_purpose`, `narrative_reason`. It must list every
   boundary once and in order, using only the five names. Anything else is rejected and never silently fixed.
3. The storyboard's `transition_in` and `transition_reason`, written by the AI during the normal storyboard stage. No extra
   model call is made, and no model is ever called while frames render.
4. The deterministic fallback. It works from narration and cast: dialogue, shocks, contrasts and changes of cast get cuts;
   time passing gets a dip; a quiet moment with the same cast gets an emotional crossfade; the same cast continuing gets a
   short crossfade. The fallback never guesses a graphic match.

The pinned profile always applies its limits:
- frame ranges;
- each still keeps at least half of itself outside the transition;
- the first scene never has a transition;
- share guardrails, which apply to the AI hints and the fallback only.

The renderer only receives validated primitives (`cut`, `crossfade`, `dip_to_dark`) plus frame counts. It never receives
code.

## Timing contract

Scene boundaries are fixed by the narration and SRT timing.

The Studio project uses the official `@remotion/transitions` `TransitionSeries` with the shared `crossfade()` (fade) and
`dipToCharcoal()` presentations. Each still is lengthened by half of each neighbouring transition, which gives:
- the midpoint of every transition sits exactly on its narration boundary;
- the series is exactly the narration length;
- no caption is shifted.

Captions, narration and music are separate absolute layers above and below the stills. A scene change therefore never
restarts or interrupts a caption.

The source checker recomputes the series. It blocks a wrong total length, other presentations (slide, wipe and so on), and
non-literal timing. It warns when an edit moves a scene change away from its narration frame.

## Captions (unchanged from Cinematic Flow)

- Font: Barlow Condensed ExtraBold, white with a strong black outline and a subtle white glow.
- Gold only on the scene's single emphasis phrase.
- A wave entrance of up to 8 frames, after which the words settle and hold still. Short exits.
- No continuous waving, shaking or pulsing.
