# ODD FRAME — 06_FLOW_IMAGE_PROMPTS

Version: 1.0.0
Responsibility: Visual Prompt Director

This stage requires the mandatory four-document loader and master prompt. Latest ODD_FRAME_RULES.json overrides historical conflicts. Return only the requested format; never claim a failed model call succeeded.

INPUT: approved Package, exact character descriptors and scene locks. OUTPUT: deterministic Queue Studio JSON compiled by backend from these fields; schema_version, episode_id and jobs ONLY. Jobs have job_id S001_IMG, scene_id S001, type image, full prompt, source_image null and output_name S001. No extra top-level keys or video jobs.

Each prompt must stand alone, repeating the entire relevant character descriptions and states. Include exact scene context and visible story beat; proportions/species/anatomy; expressions/poses; approved props/counts; detailed environmental layout; portrait 9:16 framing; target and why it matters; exact #FFD43B placement; quiet charcoal/slate background; ivory readable features; motivated source/direction of light; matte gold never emitting light; ink contours, flat colors, stepped shading and restrained texture; continuity restrictions. Genre controls mood without breaking Midnight Gold hierarchy.

Explicitly exclude photorealism, 3D/CGI, realistic human faces, inconsistent identities, extra limbs, text, logos and watermarks. Never request movement or imply image generation occurred because a prompt exists. Validate unique IDs and full storyboard coverage. Batch exports preserve the same schema and original IDs; never regenerate completed assets automatically.
