# Combined storytelling audit — before implementation

Baseline: clean production source at `4781f23`; production later received only the owner's two untracked specification files in `feat/`. Those files were read completely and are not modified. Development is isolated in `E:/facebook-storytelling-v31`, branch `feat/storytelling-intelligence-v31`. No automatic merge is authorized.

## Findings

| Area | Existing behavior | Gap against complete specifications |
|---|---|---|
| Master and rules | Version 2.0 master, 1.2 overrides; entertainment-first, 0–3 second hook, stakes by five seconds, causal progression, genre-specific payoff, no required lesson/twist/happy ending | No named Human Mirror or Retention-First extension; default remains 45–75 seconds |
| Four creative documents | Mandatory complete-byte reads, SHA/length/version/signature verification and explicit override precedence through `skills.py` | Keep originals unchanged; add a separately versioned and verified operational extension |
| Ideas | Eight stable groups/24 genres, five concepts, batch history, genre identity and diversity validation | No Human Mirror metadata or per-session preference; no structured concise retention plan |
| Writer/reviewer | Separate write then internal review, qualitative findings, physical/causal guidance and one approval gate | No structured promise/thread/ten-domain logic audit for owner inspection; no duration calibration handling |
| Package/storyboard | Coordinated full stage prompts, exact narration partition, prop/geography continuity, purposeful static stills and native transitions | Need explicit early progression, reveal alignment, optional subtext and nonbinding 12–18-still planning guidance |
| Retention audit | Ten qualitative criteria, no viral probability; ratings are editorial claims | Version 1 guidance, no first-Reel lessons or structured owner-facing preapproval retention panel |
| Human Mirror v2.1 | Related motivation/agency/non-moral principles exist | **Not implemented as specified**: no natural/subtle/none contract, meaningful-parallel consistency checks, preference, provenance or pipeline metadata. Existing general prose is not proof of a working v2.1 system |
| Analytics | Real owner JSON import, reporting period/source and nonnegative known metrics | Need observation dates/definitions, optional runtime/reach/viewers/retention notes and cautious feedback use; never derive completion from average-watch/runtime |
| Historical compatibility | Immutable per-episode/session input snapshots; exact narration approval hash, isolated workspaces and approved-source preservation | New extension must be pinned only for new work, legacy schemas must remain accepted, owner edits must not retain a false claim that prior review is current |

Code locations: `prompts/00_MASTER_PROMPT.md`, `01_IDEA_GENERATION.md`, `02_SCRIPT_WRITING.md`, `03_SCRIPT_REVIEW.md`, `04_CHARACTER_BIBLE.md`, `05_STORYBOARD.md`, `06_FLOW_IMAGE_PROMPTS.md`, `07_RETENTION_AUDIT.md`, `08_REMOTION_EDIT.md`, `11_PUBLISHING.md`; `services/api/{skills,snapshots,models,idea_models,creative,story_ideas,media,studio,main}.py`; dashboard `ideas.tsx` and Script Studio/Analytics in `main.tsx`.

## Integration decision

Retention-First v3.1 governs craft: immediate comprehensible hook, early stakes, meaningful beats, timely developments, intentional promise/thread handling and coherent physical/character logic. Human Mirror v2.1 is a subordinate, optional premise-led interpretation. Pure entertainment is a fully valid choice in every genre. No mode is assigned from genre alone. A 40–55 second pilot preference is soft, not a schema/export limit. Word budgets require measured voice evidence; actual audio/SRT remains timing authority.

Use one operational extension with both named system IDs, versioned prompt/rule updates and immutable provenance. Reuse the existing schemas, session persistence, approval gate, analytics payload storage and shadcn UI. No database migration or renderer rewrite is needed. Preserve all genre IDs and four canonical document bytes. Editorial sample review and automated contract tests will be reported separately; no sample will be called live Codex/Claude output unless actually executed.

The owner's first-Reel observations (about 107 seconds, 12-second average watch, 133 views and 12 reported unique viewers) are source-reported small-sample evidence, not independently verified Meta measurements or causal proof. They inform hypotheses about exposition, delayed stakes/discovery, repeated clues, unresolved accusation and door mechanics. No historical episode is edited and no synthetic analytics are entered as actual data.
