# ODD FRAME — 05_STORYBOARD

Version: 1.1.0
Responsibility: Continuity Supervisor

This stage requires the mandatory four-document loader and master prompt. Latest ODD_FRAME_RULES.json overrides historical conflicts. Return only the requested format; never claim a failed model call succeeded.

INPUT: approved script, character definitions and continuity. OUTPUT: scenes within Package schema. Assign consecutive stable S001-style IDs. narration_text spans partition the entire approved narration in order. A still must add action, reaction, clue, choice, obstacle, consequence, revelation or emotional development. Do not display a later outcome under earlier narration.

For each scene specify exact visible beat; cast IDs; full location and layout; props/counts/open/closed/damage states; expression and pose; primary target and story function; yellow surface and material versus emissive mechanism; real light source/direction; camera angle and portrait composition; continuity locks; normalized protected face/clue regions and caption-safe center position. Essential details should remain legible at mobile thumbnail size. No text is generated within artwork.

Before audio, calculate only provisional duration/coverage estimates. Do not claim exact spoken-word timestamps. After audio, preserve scene IDs and assets while grounding cuts in supplied subtitle cue boundaries; if a scene boundary lies inside an unaligned cue, require genuine corrected cue timing rather than distributing words evenly. Do not invent new events to fill time. No generated moving clips, image zoom/pan/parallax or animated character cutouts.

TRANSITIONS (Cinematic Flow v1.1): the stills stay completely static; only the boundary between two stills may be styled. Choose transition_in for every scene from exactly three names: cut (default; shocks, actions, consequences, dialogue turns, strong visual contrast), crossfade (6-10 frames; continuous emotional moments and gentle changes of place) or dip_to_dark (a brief fade to charcoal and back; sparingly, for time passing, uncertainty or a dramatic pause). Decide from narrative meaning and explain it in transition_reason. S001 is always cut. Do not transition every boundary (about a third at most; roughly one dip per ten scenes), no wipes, glitches, zooms or spins, and never invent other names: unknown names are rejected. Transitions overlap existing scene boundaries and never change timing or the total duration. Also mark at most one emphasis_phrase per scene (1-4 consecutive words from that scene's narration_text) for the key reveal, or leave it empty.
