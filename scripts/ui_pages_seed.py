"""Disposable UI check data: ODD_DATA_ROOT=<dir> python scripts/ui_pages_seed.py
Creates synthetic episodes (one with many exports/history) in a throw-away store so list paging and multi-delete of
exports can be exercised in a real browser without touching real episodes. Never run against the production store."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
store = Path(os.environ['ODD_DATA_ROOT']).resolve()
if store == ROOT or ROOT in store.parents and 'artifacts' not in store.parts:
    raise SystemExit('Refusing: ODD_DATA_ROOT must be a disposable folder under artifacts/')
from services.api import core, creative  # noqa: E402
from tests.fixtures import IDEA  # noqa: E402

core.init_db()
episodes = []
for i in range(1, 15):
    ep = creative.create_episode(dict(IDEA, title=f'Disposable QA story number {i:02d} {"alpha" if i % 2 else "beta"}'))
    episodes.append(ep)
target = episodes[0]
root = core.epdir(target)
(root / '07_export/final').mkdir(parents=True, exist_ok=True)
(root / '06_edit/previews').mkdir(parents=True, exist_ok=True)
entries = []
for jid in range(1, 13):
    final = root / f'07_export/final/{target["code"]}_v{jid:03d}.mp4'
    final.write_bytes(b'synthetic-mp4-' + bytes([jid]))
    preview = root / f'06_edit/previews/preview_{jid}.mp4'
    preview.write_bytes(b'synthetic-preview')
    entries.append(dict(path=f'episodes/{root.name}/07_export/final/{final.name}', preview=f'episodes/{root.name}/06_edit/previews/{preview.name}',
                        job_id=jid, created=f'2026-11-0{1 + jid % 5}T10:{jid:02d}:00+00:00', qc='PASS',
                        style=dict(profile_id='ODD_FRAME_CINEMATIC_TRANSITIONS_V1' if jid % 3 else 'ODD_FRAME_CLASSIC_V1_0')))
core.update_episode(target['id'], 'COMPLETE', exports=entries)
for n in range(1, 31):
    core.update_episode(target['id'], status=None, message=f'Synthetic history entry {n}') if False else None
print('seeded', len(episodes), 'episodes; exports on', target['code'], '; controller token in', store / 'data/controller-access.json')
