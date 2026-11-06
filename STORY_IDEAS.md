# Genre-aware story ideas v2

Create New Reel opens the Ideas page. Choose one of eight category groups, then a specific genre or Surprise Me Within This Group. The confirmation shows the resolved primary genre and current provider before any generation begins. Each confirmed batch contains exactly five validated concepts. Select a concept to continue in the existing Script Studio; script approval remains the single creative freeze gate.

`brand/STORY_GENRES.json` is the authoritative versioned taxonomy: eight groups and 24 unique genres. Its digest is registered in `brand/SKILLS_MANIFEST.json`. Master/idea/script/review prompts are version 2.0.0. Character/storyboard/edit prompts carry the same genre identity forward. The four source skill documents remain unchanged. New sessions snapshot the full taxonomy, skills, master and prompts; existing episodes and old requests retain their immutable inputs and v1 formats.

## Persistence and provider execution

The controller saves each session under `episodes/_ideas/OF_G<session-id>/`:

```
session.json                         selection, batch references, selected episodes
batches/B<batch-id>.json              immutable validated five-concept batch and provenance
.production/input_snapshot/          complete pinned creative inputs and taxonomy
.production/runs/<run-id>/            full request, attempts, validated output and status
.production/activity/<run-id>.json    bounded sequenced activity journal
```

The trusted SQLite index registers sessions and jobs. Only the existing provider adapter executes creative requests. Codex/authorized Claude retain their native isolation checks; explicit API mode retains its configured billing; manual mode exports the complete request and accepts schema-validated JSON. No credential or provider changes occur during generation. Ordinary tests never call a live model.

Concepts include primary/secondary identity, logline, premise, visual hook, characters, central conflict, escalation, ending direction, emotion, static-image feasibility, duration and ten qualitative editorial assessments. Missing fields, changed genres, invalid IDs, incomplete audits, wrong counts and near-duplicates are rejected before display. An automatic invalid response receives at most one schema-aware replacement request. Authentication, quota, cancellation and isolation errors do not trigger automatic regeneration. Invalid manual imports remain available for correction.

Repeated submission of the same idempotency key returns the existing batch. Another 5 preserves prior batches and the confirmed genre, supplies prior premise/relationship/conflict context and checks lexical similarity beyond titles. This heuristic reduces repetition; it cannot establish exhaustive originality, artistic quality or audience response. A session preserves up to 20 attempts; configured full-context limits can require a new session sooner. No request is silently truncated.

Selected episodes retain the complete concept, genre/session/batch identity and originating generation provenance. They receive their own new immutable input snapshot through the existing controller. Custom titles and optional premises are preserved as owner input. A limited explicit-wording check warns about obvious genre conflicts and requires Keep My Premise or a changed genre. It is not an authoritative semantic classifier. Title-only input is developed by the selected AI provider, never represented as an already generated concept.

## Dashboard and activity

TanStack Query loads the taxonomy, session history, provider and active batch. Saved sessions and batches can be revisited; browser preferences only remember the current view. Server records remain authoritative after refresh/navigation. The native modal dialog manages focus, Escape and background interaction; duplicate confirmation is guarded in both client and controller.

AI Activity records category confirmation, verified full-input loading, request preparation, provider activity, validation, diversity checks, saved files and selection readiness. Exact counts appear only after complete validation. Manual handoffs are labeled as waiting for import. No per-idea completion percentages or private reasoning are streamed.

## Verification and launch

Use the existing launcher: `.\scripts\start.ps1`. The launcher opens the authorized local dashboard. Open Ideas or Create New Reel. No dependencies or separate application are required.

Run `npm.cmd run build`, `.venv/Scripts/python.exe -m pytest tests/test_genre_ideas.py -q`, and `node scripts/genre-ui-smoke.mjs`. The browser script uses a disposable manual-provider store under `artifacts/genre-ui/` and synthetic concepts; it does not test live creative quality or spend model usage. Run the existing broader test suite separately for production regressions.
