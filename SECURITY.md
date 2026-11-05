# Episode production boundary

The trusted application controller/development tools are separate from episode workers. The controller allocates directories, validates typed output, writes through an episode-scoped writer and maintains the SQLite index. Development scripts intentionally upgrade shared source/configuration. No model field, prompt or dashboard operation grants an episode development privileges.

## Native enforcement

Every automatic CLI generation, asset-validation process and render worker uses the installed Codex CLI's **Windows MXC** sandbox with exact episode permissions. No weaker/unrestricted fallback is attempted. Shared files are read-only; snapshots/provenance and approved narration are read-only; controller state/secrets are denied. Real subprocess write-denial checks, inherited-child checks, an AppContainer token and non-elevation must pass before execution. Unsupported isolation disables automatic workers, including rendering; manual structured import remains usable.

A Windows Job Object with KILL_ON_JOB_CLOSE binds workers/descendants to the controller lifetime. Timeout/cancellation kills the tree. Restart marks interrupted AI requests for explicit retry, requeues deterministic render jobs and removes interrupted private auth homes.

MXC itself provisions OS-managed private container/runtime state. Application outputs, CLI state, logs, intermediate audio, multipart spools, webpack bundles and Remotion media caches are redirected beneath the episode root. No shared application/temp cache is granted writable. Native bootstrap is distinct from episode deliverables; unsupported Windows builds/other operating systems are not claimed to have equivalent enforcement.

## Episode data

```
.production/
  input_snapshot/       complete pinned brand/prompts and small Remotion templates
  provenance.json       source versions/hashes, template/music identity
  locks/                per-episode cross-process locks
  runs/<UUID>/          request/schema/response/validated result/retry state
  jobs/<ID>.json        authoritative local render progress
  temp/<job-ID>/        unique writable work area
  logs/                 local diagnostics and boundary evidence
  runtime/              private job homes; never served through HTTP
production_status.json  authoritative episode state/history
episode.json            identity and compatible local mirror
```

New episodes pin all four complete skills, rules, master and stage prompts. Only the small component/renderer and dependency manifests are copied, not the application tree. Shared native media dependencies remain read-only and hash-pinned; updates block rather than silently change existing output. Later creative upgrades apply to new episodes; existing requests reread their full immutable snapshot.

Configured ODD_SIGNATURE_MUSIC is copied/versioned/hashed at bootstrap. Otherwise a validated owner instrumental is pinned on import. Global updates or different imports cannot replace it silently. Rights evidence is preserved, never fabricated. Exactly narration plus instrumental; no SFX.

## File writer and links

EpisodeWriter rejects absolute/UNC/device paths, traversal, alternate streams, invalid filenames, symlinks/junctions/reparse points and hard links. Exclusive unique temps and atomic replacement protect generated documents. Windows ancestor handles omit FILE_SHARE_DELETE to prevent parent replacement while opening/writing; paths are rechecked at mutation time. Rename/delete are episode-relative and cannot target immutable inputs. Lock files serialize conflicting same-episode operations independently of other episodes.

A full preflight rejects pre-existing links before production launch. This is necessary: testing found that an existing writable hard-link alias could otherwise open its external inode. Native tests separately confirm that creation of a new external hard link and writing through a junction are denied. The writer rejects these aliases independently. No AI-generated shell commands or arbitrary output paths are executed. Installation/source-generation scripts are development-only.

## Controller and database

Workers cannot open global SQLite: the code rejects it and the OS denies the controller data directory. They persist local status/progress; only the trusted controller maintains the read-derived index. A localhost write cannot bypass this: mutations require a random controller capability unavailable to workers. The launcher passes it to the owner's browser in a URL fragment; JavaScript moves it to sessionStorage and removes the fragment. It is not an AI credential. Use scripts/start.ps1 to authorize write controls.

All private .production files are excluded from generic file/media downloads. Public creative documents remain downloadable. Host/Origin protections remain enabled. Model tools are read-only/disabled; the separate outer OS boundary constrains the CLI process and all children even if an inner setting changes.

## Existing Remotion pipeline

The same static-image/animated-center-caption composition is retained. Its pinned source bundles only into the episode cache and serves that episode's media. It never rewrites node_modules/shared components. The bundled dynamic Windows FFmpeg/FFprobe crashed in MXC here. Development setup prepares a shared read-only runtime from the installed static tools plus unchanged Remotion compositor libraries. A small reviewed native launcher translates filter-script flags removed in FFmpeg 9 and selects the installed native AAC encoder. This uses Remotion's documented [binariesDirectory](https://www.remotion.dev/docs/options/binaries-directory), not a second renderer. Runtime hashes are pinned. Actual isolated preview/final output passed technical QC.

## Evidence and scope

scripts/isolation_smoke.py runs two real native workers concurrently. Tests cover shared prompt/skill/music/component writes, root/sibling writes, absolute/traversal paths, junctions/new external hard links, snapshots, child processes, controller-capability reads, caches, sibling deletion/rename, authorized writes, isolated test exports and lock conflicts. Integrity hashes supplement actual permission tests. Hostile pre-existing fixtures are rejected by normal preflight; the harness separately exercises raw OS attempts.

See VERIFICATION.md. The authorized host owner/development code remains outside the production boundary by design; an episode prompt cannot acquire its authority. Technical isolation does not establish artistic quality, licensing, acoustic sync or audience performance.
