---
name: odd-frame-typography-and-motion
description: Apply a consistent typography and editorial-motion system to Odd Frame cinematic 2D story Reels using charcoal, ivory, and golden yellow.
version: 1.0
---

# Odd Frame — Typography and Motion Guide

Brand: **Odd Frame**, suggested handle **@OddFrameStories**.
Companion to the existing yellow-and-charcoal 2D still design guide. That guide carries the former Say It Better name; use Odd Frame in new outputs. This file is a portable production reference, not an automatically installed skill.

## 1. Research findings versus creative decisions

Barlow's designer offers normal, semi-condensed, and condensed families. Atkinson Hyperlegible Next was developed for legibility, including distinguishing similar characters, and its publisher permits personal and commercial applications. Remotion supports frame-driven animation, interpolation, springs, and scene transitions.

The particular font pairing, sizes, timings, and motion amounts below are **proposed Odd Frame production defaults**, not experimentally proven retention settings. Test them on your actual artwork, narration, and phone screen. No font or transition guarantees reach.

## 2. Font system

| Role | Font | Weight | Reason for this selection |
| --- | --- | --- | --- |
| Opening hook and short reveal | Barlow Condensed | ExtraBold 800 | Compact, strong display shape that leaves room for the illustration |
| Secondary line and explanatory label | Atkinson Hyperlegible Next | SemiBold 600 | Distinct letterforms and a more open reading texture |
| Optional narration captions | Atkinson Hyperlegible Next | Bold 700 | Consistency with supporting text; clear short phrases |
| Optional editorial sound word | Barlow Condensed | ExtraBold 800 | Same display identity without adding another font |

Use only these two families in the standard system. Do not switch fonts to imitate each genre. Change wording, layout, weight, and motion instead. These are recommended fonts, not an identification of the reference page's exact typeface.

Download from the sources at the end. Retain the font license files with production assets. Do not assume a font already installed on an editor's machine may be redistributed. Load actual font files before measuring or rendering text; do not rely on synthetic bold or a silent fallback.

## 3. Type scale for a 1080 × 1920 master

| Element | Starting size | Limits |
| --- | --- | --- |
| Opening hook | 88–112 px | 2–6 words, generally one or two lines |
| Major reveal | 80–104 px | One short phrase; no paragraph |
| Supporting line | 52–64 px | One or two short lines |
| Optional narration captions | 56–68 px | Maximum two lines; phrase-level grouping |
| Story label | 44–52 px | Only if essential; verify on phone |

Measure the actual text width. Rewrite or rebreak an overlong hook before reducing the font below the intended role. Never stretch letters horizontally. Start with line height 0.98–1.08 for display hooks and 1.12–1.22 for supporting text. Keep tracking close to normal; test slight positive tracking for short uppercase labels only.

Use uppercase for brief hooks such as “THE KEY WAS INSIDE.” Use sentence case for longer supporting phrases. Keep punctuation intentional. Avoid continuous all-caps narration, long italics, and thin weights.

These sizes are design starting points. Font metrics, wording, and viewing conditions affect the final choice.

## 4. Text color and position

- Primary text: warm ivory **#F1EBDD**.
- Emphasis: golden yellow **#FFD43B**, normally one meaningful word or a short phrase.
- Backing: charcoal **#14171C**, either a quiet illustration area or a restrained opaque/translucent panel when necessary.
- Small supporting text should use a solid readable color; do not lower opacity until it disappears into the artwork.
- Add a subtle charcoal shadow or a 3–5 px outline only when needed. Avoid thick sticker outlines, neon borders, and bevels.

**Share the attention budget with the image.** If a yellow key is the focal point, keep the hook ivory. If the hook is the intended first look, it may contain one yellow word while the illustration stays quieter. Do not create two unrelated yellow focal points.

At 1080 × 1920, start by keeping essential text inside x=90–890 and y=200–1490. This is a conservative composition guide, not a guaranteed Facebook safe area. Check the current interface. Keep captions above the lower controls and clear of faces, hands, and clues.

Select a stable text zone within each scene. Never let captions jump between random corners or change font size for every phrase. Avoid simultaneous hook text, labels, speech bubbles, and narration captions.

**Default: no burned-in narration captions unless the episode brief requests them.** Short editorial hooks and story labels are separate choices. Text must add meaning; a text-free scene is valid. Add accurate typography in the editor rather than asking the image generator to draw it.

## 5. Motion principle

Every movement must have a purpose: introduce information, guide attention, connect scenes, or express a reaction. A new clue or consequence is more useful than movement added to an unchanged story beat.

Default to a stable camera and purposeful cuts. Do not apply automatic zoom/pan to all stills. Do not distort a character's face, imply an action that did not happen, or use a transition that obscures a clue.

Choose at most one dominant motion and one subtle secondary effect per shot. Narration, music, sound effects, and cuts can carry energy even when the illustration stays still.

## 6. Text motion presets at 30 FPS

| Preset | Settings | Appropriate use |
| --- | --- | --- |
| Soft arrival | Fade 0→1 and rise 18 px over 6–8 frames; then remain still | Most short hooks and labels |
| Immediate reveal | Hard cut to fully visible text | Twist, blunt statement, comic payoff |
| Gentle emphasis | Scale 0.97→1.00 over 6–8 frames with ease-out; no bounce | One important word or reveal |
| Quiet exit | Fade over 4–6 frames | Only when text must leave before the scene ends |
| Phrase replacement | Replace the entire phrase at a narration boundary | Optional captions |

Timings are recommendations. Convert seconds to frames for other frame rates. Keep text fully legible during its main reading period; entrance and exit frames do not count as full reading time.

Start with 1.3–2.2 seconds of fully readable time for a 3–6-word hook, then adjust to narration and complexity. Longer phrases need longer. Read each screen aloud and verify on a phone. Never reveal a key word after the spoken reveal unless the delay is intentional.

Avoid per-letter spinning, constant word bouncing, rapid karaoke colors, elastic wobble, and typewriter effects for ordinary narration. A typewriter effect is acceptable for a deliberately staged short message if it does not delay comprehension.

## 7. Still-image motion presets

| Preset | How to build it | Asset requirement |
| --- | --- | --- |
| Static cinematic hold | Keep artwork stable; use sound and a meaningful next cut | One flattened still |
| Detail cut | Cut from the full scene to a closer crop of the clue | Enough source resolution and a crop that preserves context |
| Attention reveal | Briefly reduce a local dimming overlay to expose the clue | Accurate mask; underlying clue already present |
| Motivated light change | Small, nonrepetitive brightness change from a lamp/window | Isolated source mask and consistent reflected light |
| Layered atmosphere | Very subtle fog, rain, or drifting dust when the setting needs it | Separate overlay; must not cover the clue |
| Controlled parallax | Very small relative layer movement, only when deliberately planned | Separate clean foreground, subject, and background assets with filled hidden areas |

Do not claim a flattened JPG has independent character or object motion. A detail crop is a new editorial framing, not character animation. Do not invent mouth motion, blinking, hand movement, or walking by warping the still.

Parallax is optional, not the default. Do not introduce a 3D orbit, artificial depth blur, or moving cutout edges that break the drawn style. Camera motion requires a deliberate shot choice; otherwise use cuts.

## 8. Scene changes and pacing

Use hard cuts for most changes in information. Use a short dissolve for a softer emotional connection or passage of time. Use a restrained wipe or occlusion transition only when the scene provides a plausible object or shape for it.

Starting transition durations at 30 FPS:

- Hard cut: 0 frames.
- Short dissolve: 6–10 frames.
- Reflective time passage: 10–15 frames if the images remain readable.
- Text entrance: usually 6–8 frames, independent of scene transition.

Do not put a transition effect on every cut. Avoid routine spins, cube rotations, glitch cuts, white flashes, and aggressive zoom transitions. A yellow brand color does not justify a yellow flash between scenes.

Start with 2–4-second story beats where appropriate. A reaction may need less time; a spatially complex reveal may need more. If a still needs a longer hold, give the audience something meaningful to discover or introduce a detail cut. Do not cut on a timer while the sentence or visual action is unfinished.

Never use strobing as a retention device.

## 9. Genre motion choices

| Genre | Motion and edit treatment |
| --- | --- |
| Mystery | Stable setup, selective detail cut, brief hold before or after the reveal |
| Comedy | Clear setup, exact reaction cut, immediate readable punchline; a small single spring accent is optional |
| Sadness/romance | Longer readable holds, restrained text arrivals, occasional soft dissolve |
| Adventure | Directionally coherent cuts and clear geography; use action sound to connect scenes |
| Horror | Quiet staging and deliberate interruption; avoid constant shake and flashing |
| Betrayal/revenge | Establish object ownership and eyelines clearly; cut to evidence, reaction, consequence |

Do not force one editing tempo across every genre. Maintain identity through palette, fonts, illustration, and restrained transitions.

## 10. Example opening: “The key was inside”

This is an illustrative timing example, not a completed story.

| Time | Image and motion | Text |
| --- | --- | --- |
| 0.0–1.5 s | Stable close view of a locked transparent box containing a yellow key | “THE KEY WAS INSIDE.” Ivory; arrive over 6 frames |
| 1.5–2.8 s | Hard cut wider: a rabbit holds an identical key | None; let the contradiction read |
| 2.8–4.2 s | Cut to the matching key and the rabbit's confused face | “So who locked it?” only if narration/story benefits |
| 4.2 s onward | Next still adds evidence or a consequence | No automatic title card or logo bumper |

Keep the original key yellow in subsequent scenes. Change prominence through framing and light rather than recoloring props.

## 11. Remotion implementation rules

Drive animations from the current frame and composition FPS. Use interpolation for controlled opacity/position and springs only for deliberate spring motion. Avoid wall-clock timers, nondeterministic randomness, and CSS transitions that can produce inconsistent renders.

Use clamped animation ranges so text remains stable after entering. Load fonts before measuring text or rendering. Render a sample with actual font files and actual dialogue, not only placeholder strings.

When using TransitionSeries, account for overlaps: scene transitions shorten the combined duration because the adjacent scenes render simultaneously. A simple two-scene example with 90 frames each and a 10-frame overlap lasts 170 frames, not 180. Preserve narration synchronization and the final ending hold. Check installed Remotion package versions before using newer APIs; match related package versions.

## 12. Required motion brief per shot

```yaml
scene_id: S001
story_change: "What new information appears?"
primary_visual_target: "The clue or interaction"
text_role: "none / hook / label / optional captions"
text_exact: "Approved wording"
font_and_weight: "Barlow Condensed 800"
text_color: "Ivory; yellow emphasis only if justified"
text_position: "Clear of clue, face, and controls"
entrance: "6-frame fade and 18px rise"
fully_readable_duration: "Set from wording and narration"
image_motion: "static / detail cut / masked reveal / planned layers"
asset_requirements: "Flattened still or named separated layers"
transition_out: "Hard cut"
audio_cue: "Specific narrative cue or none"
continuity_check: "Prop, light, and geography constraints"
```

## 13. Final review

- Fonts loaded correctly; no fallback, fake bold, or stretched letters.
- Hook understandable without watching its entrance twice.
- Type clear on a phone-sized preview and over the actual illustration.
- Yellow text does not compete with the yellow story clue.
- No text or crop hides a critical face, gesture, or prop.
- One dominant motion; no automatic pan/zoom or repeated unnecessary effects.
- Separate-layer effects used only when suitable assets exist.
- Every shot changes the story or supports an intentional pause.
- Narration timing survives transition overlaps.
- Ending remains long enough to understand the payoff.
- No claim that these defaults are proven viral settings.

## 14. Primary research sources

Checked November 5, 2026. Source facts support font availability/design and technical capabilities; the art direction above is our recommendation.

- Barlow designer's official page and family links: https://tribby.com/fonts/barlow/
- Barlow Condensed specimen: https://fonts.google.com/specimen/Barlow+Condensed
- Braille Institute font descriptions and usage information: https://www.brailleinstitute.org/freefont/
- Atkinson Hyperlegible Next release: https://www.brailleinstitute.org/about-us/news/braille-institute-launches-enhanced-atkinson-hyperlegible-font-to-make-reading-easier/
- Remotion animation APIs: https://www.remotion.dev/docs/api
- Remotion animation math: https://www.remotion.dev/docs/animation-math
- Remotion transitions and duration behavior: https://www.remotion.dev/docs/transitioning
- Remotion transition package: https://www.remotion.dev/docs/transitions/
