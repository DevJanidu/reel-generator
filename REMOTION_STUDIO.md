# Editing in the official Remotion Studio

ODD FRAME no longer ships its own browser video editor. The dashboard stays the workflow manager; editing happens in the
**real Remotion Studio** (`@remotion/cli` 4.0.541, the same version as the renderer) running locally.

## How to use it (beginner guide)

1. Approve the script, generate the stills, narration, SRT and import them as usual (Asset Manager).
2. **Edit Studio** → choose your reel → **Auto Edit → build Studio project**. The station validates the assets, builds the
   timeline from your real narration/SRT timing, picks scene transitions and caption effects, and writes a complete
   Remotion project for this episode. Watch **AI Activity** for the real stages. Nothing is rendered to MP4 at this point.
3. Click **Open in Remotion Studio**. The panel shows the real start-up steps (Checking assets → Starting Remotion Studio →
   Ready to edit). When it says **Remotion Studio Ready — Open Editor**, click it. Studio opens in a new tab on a free
   `127.0.0.1` port with your composition (id such as `OF-R001`) already assembled.
4. Make small adjustments (see below). Studio saves them into the episode's own source files. Refresh, restart Studio or the
   dashboard: your edits are still there.
5. Click **Render final MP4 from this Studio project** in the dashboard. It renders exactly the source you reviewed, then runs
   the usual loudness/true-peak, decode, black-frame and duration QC and writes a new versioned export (older exports are never
   overwritten). You can also use Studio's own Render button for a quick local test render.

## What you can change

| Where | What |
|---|---|
| Studio **props panel** (saved to `src/Root.tsx`) | narration gain (0–2×), music gain (0–2×), music fade in/out, extra narration-priority ducking, caption glow strength |
| Studio **timeline** | `STORY — stills + transitions` (the official TransitionSeries) with every still `S001 — …` inside it; every caption phrase (`CAP001 — …`), `NARRATION — ElevenLabs` and `MUSIC — Signature Instrumental` is its own named sequence. Scrub / step frame by frame (← →) through any transition and play it back. Caption sequences can be dragged/trimmed (saved to `src/Episode.tsx`); dragging stills inside the TransitionSeries was not tested. |
| **Source only** (`06_edit/studio/src/Episode.tsx`) | caption text, animation preset, gold emphasis, vertical position, enter/exit frames; scene transitions: each boundary is a commented `<TransitionSeries.Transition presentation={crossfade()} timing={transitionTiming(7)} />` (or `dipToCharcoal(...)`), hard / graphic-match cuts have no element. Studio has no drag-and-drop transition editor. |

Limits worth knowing: the stills live in one official `TransitionSeries` ("STORY — stills + transitions"), so changing one still's
duration shifts the later stills but not the captions or audio. The checker warns when a scene change leaves its narration
frame and blocks a wrong total length. Transition rules and who decides them: EDITING_TRANSITIONS.md. the first Studio launch compiles the project (about
6–10 s measured here).

Not allowed (checked at launch and again before export): image movement (pan/zoom/rotate/scale/offset/keyframes on stills),
extra `<Audio>`/video elements or sound effects, a missing still, gaps without a still, more or fewer than one narration and one
music sequence.

## Where things live

`episodes/<EP>/06_edit/studio/`
- `src/Episode.tsx`, `src/Root.tsx`: generated once, then **yours**. These are the source of truth for export.
- `src/lib/`: pinned copy of the shared effect components (`StaticStoryScene`, `WaveCaption`, `GlowCaption`, `SmoothPhraseCaption`,
  `CaptionSwitcher`, `HardCutTransition`, `CrossfadeTransition`, `DipToDarkTransition`, `NarrationTrack`, `MusicTrack`,
  `SignatureAudioMix`). Hash-checked; production never edits the shared originals in `video/remotion/src`.
- `public/`: copies of this episode's stills, the two audio files and the two fonts. Studio serves only this folder.
- `studio.manifest.json`: hashes, provenance, the Auto Edit revision it was built from.
- `revisions/`: archives of the source before any regeneration and before every export (`render-<job>`).

## Safety model

- Studio is started by the trusted controller with a fixed executable and an argument list whose only variable is a free port,
  bound to `127.0.0.1`. It runs inside the same verified Windows MXC sandbox as the production workers: it can write only its own
  episode folder; other episodes, shared code, `data/` and `.env` are read-only or denied. If the boundary cannot be verified Studio
  is not started. The process is tied to the station (Job Object) and stopped with it; at most two Studios run at once.
- Shared dependencies come from the application's `node_modules`; nothing is installed per episode.
- Rebuilding never overwrites your edits unless you tick **Replace my Studio edits**; the old source is archived first.
- Studio itself contacts `bugs.remotion.dev` from your browser (version check). Disable it by blocking that host if you prefer.

## Retired

The custom Live Editor route now only shows a notice. Its backend (`/api/episodes/{id}/editor*`) and drafts are kept because Auto
Edit still produces the measured timeline and audio mix that the Studio project is built from.
