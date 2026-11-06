"""Development/controller tool: migrate ONE episode to ODD_FRAME_CINEMATIC_TRANSITIONS_V1 with reviewed decisions.

    python scripts/apply_transition_decisions.py --episode-id 1 --decisions path/to/transition_decisions.json

Explicit owner-authorized migration. Adopts the profile (the original pinned files are never rewritten), validates and
installs the per-boundary decisions file, then queues the normal sandboxed Auto Edit rebuild, which keeps owner Studio edits
unless --replace-studio-edits is given (the old source is archived first either way). Approved narration, stills, audio
and earlier exports are not touched.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.api import core, main, styles, studio  # noqa: E402
from services.api.file_writer import EpisodeWriter  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument('--episode-id', type=int, required=True)
parser.add_argument('--decisions', type=Path, required=True)
parser.add_argument('--replace-studio-edits', action='store_true')
args = parser.parse_args()

ep = core.episode(args.episode_id)
directory = core.epdir(ep)
edits = studio.owner_changes(directory)
if edits and not args.replace_studio_edits:
    raise SystemExit('The Studio project has owner edits in ' + ', '.join(edits) + '. Re-run with --replace-studio-edits to rebuild (archived first).')
scenes = ep['data']['package']['scenes']
raw = args.decisions.read_bytes()
# Validate BEFORE anything is written.
probe = ROOT / 'artifacts/.decision-probe'
(probe / '06_edit').mkdir(parents=True, exist_ok=True)
(probe / styles.DECISIONS_PATH).write_bytes(raw)
styles.load_decisions(probe, scenes)
if (ep['data'].get('style') or {}).get('profile_id') != styles.TRANSITIONS_ID:
    main.set_style(args.episode_id, dict(profile_id=styles.TRANSITIONS_ID, adopt=True))
writer = EpisodeWriter(directory)
target = directory / styles.DECISIONS_PATH
if target.is_file() and target.read_bytes() != raw:
    writer.bytes(styles.DECISIONS_PATH.replace('.json', '.' + core.now().replace(':', '').replace('-', '')[:15] + '.previous.json'), target.read_bytes(), replace=False)
writer.bytes(styles.DECISIONS_PATH, raw)
result = main.rebuild_editor(args.episode_id, dict(replace_studio_edits=args.replace_studio_edits))
print(json.dumps(dict(episode=ep['code'], style=core.episode(args.episode_id)['data']['style'], decisions=styles.DECISIONS_PATH,
                      rebuild=result if not isinstance(result, dict) else {k: result[k] for k in result if k in ('job_id', 'status', 'message')}), indent=2))
