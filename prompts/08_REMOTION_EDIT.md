# ODD FRAME — 08_REMOTION_EDIT

Version: 1.1.0
Responsibility: Timeline Editor + Typography Director

This stage requires the mandatory four-document loader and master prompt. Latest ODD_FRAME_RULES.json overrides historical conflicts. Return only the requested format; never claim a failed model call succeeded.

INPUT: approved script hash, validated stills, actual narration duration, SRT cues or genuine alignment, storyboard scene spans and protected_regions. OUTPUT: timeline.json plus captions.json using measured cue evidence. Caption and shot boundaries must be narration-grounded. Do not derive fake word timestamps by equal division of a long SRT cue.

STATIC illustrations only, full portrait frame without stretching. No image transforms, zoom/pan, parallax, character animation, generated video or effects layers on the artwork. Scene boundaries use the validated transition_in of the episode's pinned editing profile: hard cut, smooth crossfade (6-10 frames) or dip to charcoal, layered over unchanged boundaries so narration synchronization and total duration never change. Ensure no gaps/overlaps, no ending reveal early and no conclusion illustration under prior narration. If supplied SRT crosses scene boundaries or has more than four words per cue without alignment, show actionable correction requirements.

Required centered captions: Barlow Condensed ExtraBold 800; white, strong black outline, subtle shadow; max two lines, 1–4 words per synchronized phrase, scene-stable location near .46 height unless face/clue regions require relocation. Load licensed font files. Classic v1.0 uses Quick Pop (scales .94→1 over 4–6 frames with a fast fade then a stable hold). Cinematic Flow v1.1 (default for new episodes) uses Wave Reveal (staggered letters rise with a smooth wave over 5–8 frames, then stay perfectly still), Smooth Phrase Replace for continuous phrases, Glow Pop with restrained golden-yellow emphasis for the key reveal, Immediate Impact when narration is fast and Soft Fade for quiet moments. Fill stays white with a thick black outline and a soft white glow that rises briefly as a phrase lands and then settles; no constant pulsing or blur. Only text animates. No caption before its speech cue. Export frame-based deterministic composition at 1080×1920 30 FPS. Exactly narration plus instrumental sources.
