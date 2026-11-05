"""Disposable Preview Style demonstration. Renders Classic v1.0 and Cinematic Flow v1.1 sample footage (labelled SAMPLE)
in a throw-away store, then extracts inspectable frames. Never touches production episodes or exports.

    .\\.venv\\Scripts\\python.exe scripts\\style_demo.py
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RUN = ROOT / 'artifacts' / 'style-demo' / time.strftime('%Y%m%d-%H%M%S')
RUN.mkdir(parents=True, exist_ok=False)
os.environ['ODD_DATA_ROOT'] = str(RUN)
os.environ['ODD_AI_PROVIDER'] = 'manual'
from services.api import core
core.init_db()
(core.STORE / 'episodes').mkdir(parents=True, exist_ok=True)
from services.api.creative import create_episode
from services.api.core import epdir, episode
from services.api.media import command
from tests.fixtures import IDEA


def main():
    ep = create_episode(IDEA)
    eid = ep['id']
    directory = epdir(episode(eid))
    print('Disposable store:', RUN, flush=True)
    print('New episode style pin:', episode(eid)['data']['style'], flush=True)
    os.environ.update(ODD_EPISODE_WORKER='1', EPISODE_WRITE_ROOT=str(directory), ODD_APP_ROOT=str(ROOT), ODD_JOB_ID='style-demo')
    from services.api import worker
    meta = worker.style_preview(eid, ['ODD_FRAME_CLASSIC_V1_0', 'ODD_FRAME_CINEMATIC_FLOW_V1_1'])
    print(json.dumps(meta, indent=2), flush=True)
    frames = RUN / 'frames'
    frames.mkdir()
    marks = {'ODD_FRAME_CLASSIC_V1_0': [8, 45, 120], 'ODD_FRAME_CINEMATIC_FLOW_V1_1': [4, 6, 8, 12, 45, 108, 112, 118, 168, 171, 175, 215]}
    for item in meta['profiles']:
        video = core.STORE / item['file']
        for frame in marks.get(item['profile_id'], []):
            target = frames / f"{item['profile_id'].split('_')[2]}_f{frame:03d}.png"
            command(['ffmpeg', '-y', '-v', 'error', '-i', video, '-vf', f'select=eq(n\\,{frame // 1})', '-frames:v', '1', target])
    print('Frames:', frames)
    print('Videos:', [str(core.STORE / p['file']) for p in meta['profiles']])


if __name__ == '__main__':
    main()
