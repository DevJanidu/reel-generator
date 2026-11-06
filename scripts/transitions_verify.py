"""Disposable verification of ODD_FRAME_CINEMATIC_TRANSITIONS_V1 on a COPY of a real episode (default OF_R001).

Development tool. No model usage and no full MP4 export: the real sandboxed Auto Edit builds the Studio project in a
disposable store, then single frames around every transition (and one short clip) are rendered from that exact Studio
source and measured. The original episode is hash-checked before and after and never written.

    python scripts/transitions_verify.py --decisions path/to/transition_decisions.json [--baseline]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser()
parser.add_argument('--episode', default='OF_R001_the-key-was-outside')
parser.add_argument('--decisions', type=Path, required=True)
parser.add_argument('--baseline', action='store_true', help='Also time the same frames on the episode\'s current (pre-upgrade) Studio project')
args = parser.parse_args()
store = ROOT / 'artifacts/transitions-v1' / time.strftime('run-%Y%m%d-%H%M%S')
store.mkdir(parents=True, exist_ok=False)
os.environ.update(ODD_DATA_ROOT=str(store), ODD_AI_PROVIDER='manual', ODD_TEST_RUN='1')
from PIL import Image, ImageChops, ImageStat  # noqa: E402
from services.api import core, worker, editor, styles, studio, isolation  # noqa: E402

NODE = shutil.which('node')


def tree_hashes(base):
    return {p.relative_to(base).as_posix(): core.sha(p.read_bytes()) for p in base.rglob('*')
            if p.is_file() and '.production/runtime' not in p.as_posix() and '/node_modules/' not in p.as_posix()}


def preview(studio_dir, comp, out, frames, clip=None):
    cmd = [NODE, str(ROOT / 'video/remotion/preview-studio.mjs'), str(studio_dir), comp, str(out), '--frames', ','.join(map(str, frames))]
    if clip:
        cmd += ['--range', f'{clip[0]}-{clip[1]}']
    started = time.perf_counter()
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800,
                         env={**os.environ, 'ODD_APP_ROOT': str(ROOT)})
    if run.returncode:
        raise RuntimeError(run.stderr[-3000:] or run.stdout[-3000:])
    result = core.read_json(out / 'preview.json')
    result['wall_seconds'] = round(time.perf_counter() - started, 2)
    return result


def luma(path):
    return ImageStat.Stat(Image.open(path).convert('L')).mean[0]


def diff(a, b, box=None):
    x, y = Image.open(a).convert('L'), Image.open(b).convert('L')
    if box:
        x, y = x.crop(box), y.crop(box)
    return ImageStat.Stat(ImageChops.difference(x, y)).mean[0]


def main():
    core.init_db()
    source = ROOT / 'episodes' / args.episode
    before = tree_hashes(source)
    dest = store / 'episodes' / source.name
    dest.mkdir(parents=True)
    for name in ['00_brief', '01_script', '02_characters', '03_storyboard', '04_google_flow', '05_assets']:
        shutil.copytree(source / name, dest / name)
    for name in ['episode.json', 'production_status.json']:
        shutil.copy2(source / name, dest / name)
    (dest / '.production').mkdir()
    (dest / '07_export/final').mkdir(parents=True)
    shutil.copytree(source / '.production/input_snapshot', dest / '.production/input_snapshot')
    shutil.copy2(source / '.production/provenance.json', dest / '.production/provenance.json')
    original = core.read_json(dest / 'episode.json')
    with core.db() as c:
        c.execute('INSERT INTO episodes(id,code,path,title,status,data,updated) VALUES (?,?,?,?,?,?,?)',
                  (original['id'], original['code'], original['path'], original['title'], original['status'], json.dumps(original['data']), original['updated']))
    core.update_episode(original['id'], 'AWAITING_ASSETS', exports=[], error=None)
    report = dict(store=str(store), at=core.now(), episode=original['code'])

    # 1. Explicit adoption of the new profile + the editorial decisions, on the copy only.
    adopted = styles.pin_style_upgrade(dest, styles.TRANSITIONS_ID)
    core.update_episode(original['id'], style=adopted)
    (dest / styles.DECISIONS_PATH).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.decisions, dest / styles.DECISIONS_PATH)
    scenes_pkg = core.episode(original['id'])['data']['package']['scenes']
    styles.load_decisions(dest, scenes_pkg)

    # 2. The real sandboxed Auto Edit (same job the dashboard queues).
    started = time.perf_counter()
    jid = worker.enqueue(original['id'], 'draft')
    with core.db() as c:
        job = dict(c.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone())
    worker.run_isolated_render(job)
    report['auto_edit_seconds'] = round(time.perf_counter() - started, 2)
    report['isolation'] = isolation.status(dest)

    # 3. Timing: identical boundaries, duration and captions to the pre-upgrade edit.
    m = studio.manifest(dest)
    old_m = core.read_json(source / '06_edit/studio/studio.manifest.json')
    check = studio.check_source(dest)
    old_caps = core.read_json(source / '06_edit/captions.json')
    new_caps = core.read_json(dest / '06_edit/captions.json')
    report['timing'] = dict(
        frames=m['durationInFrames'], seconds=round(m['durationInFrames'] / 30, 3), previous_frames=old_m['durationInFrames'],
        scene_boundaries_unchanged=[(s['start'], s['end']) for s in m['scenes']] == [(s['start'], s['end']) for s in old_m['scenes']],
        series_end=check['scenes'][-1]['end'], series_matches_narration=check['scenes'][-1]['end'] == m['durationInFrames'] == check['total_frames'],
        transition_midpoints_on_boundaries=all(t['boundary'] == next(s['start'] for s in m['scenes'] if s['id'] == t['to']) for t in check['transitions']),
        captions=len(new_caps), captions_unchanged=[(c['start'], c['end'], c['text']) for c in new_caps] == [(c['start'], c['end'], c['text']) for c in old_caps],
        source_errors=check['errors'], source_warnings=check['warnings'])
    report['decisions'] = [dict(boundary=f"{a['id']}→{b['id']}", at_frame=b['start'], transition=b['editorial'], frames=b['transition_frames'], reason=b['reason'])
                           for a, b in zip(m['scenes'], m['scenes'][1:])]
    counts = {}
    for d in report['decisions']:
        counts[d['transition']] = counts.get(d['transition'], 0) + 1
    report['distribution'] = counts

    # 4. Real frames around every boundary, rendered from the exact Studio source.
    probes = {}
    for a, b in zip(m['scenes'], m['scenes'][1:]):
        t, s = b['transition_frames'], b['start']
        if t:
            pre, post = s - t // 2 - 1, s + (t - t // 2)
            probes[b['id']] = dict(kind=b['editorial'], boundary=s, frames=[pre, s - t // 2, s - 1, s, post - 1, post])
        else:
            probes[b['id']] = dict(kind=b['editorial'], boundary=s, frames=[s - 1, s])
    wanted = sorted({f for p in probes.values() for f in p['frames']})
    clip = next(((b['start'] - 20, b['start'] + 20) for b in m['scenes'] if b['editorial'] == 'emotional_crossfade'), None)
    out = store / 'frames-new'
    new_preview = preview(studio.studio_dir(dest), m['composition_id'], out, wanted, clip)
    report['preview_new'] = {k: v for k, v in new_preview.items() if k != 'stills'}
    report['preview_new']['still_ms_mean'] = round(sum(x['ms'] for x in new_preview['stills']) / len(new_preview['stills']))
    frame = lambda f: out / f'frame-{f:05d}.png'
    art = (0, 0, 1080, 560)   # upper picture area, above every caption zone of this episode
    results = {}
    for sid, p in probes.items():
        f = p['frames']
        if len(f) == 2:
            results[sid] = dict(kind=p['kind'], change_at_boundary=round(diff(frame(f[0]), frame(f[1]), art), 2),
                                luma=[round(luma(frame(x)), 1) for x in f])
        else:
            lum = [round(luma(frame(x)), 1) for x in f]
            results[sid] = dict(kind=p['kind'], luma=lum,
                                held_before=round(diff(frame(f[0]), frame(f[1]), art), 2),           # first transition frame ~ still A
                                held_after=round(diff(frame(f[4]), frame(f[5]), art), 2),            # last transition frame ~ still B
                                darkest_frame_luma=min(lum))
    report['frames'] = results
    report['no_pure_black_frame'] = all(min(r['luma']) > 8 for r in results.values())
    report['crossfades_without_luminance_dip'] = all(
        min(r['luma'][1:5]) >= min(r['luma'][0], r['luma'][5]) - 3 for r in results.values() if 'crossfade' in r['kind'])
    if clip:
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height,r_frame_rate:format=duration',
                                '-of', 'json', new_preview['clip']['output']], capture_output=True, text=True)
        report['clip_probe'] = json.loads(probe.stdout)

    if args.baseline:
        base_out = store / 'frames-baseline'
        base = preview(source / studio.STUDIO_DIR, old_m['composition_id'], base_out, wanted, clip)
        report['preview_baseline'] = {k: v for k, v in base.items() if k != 'stills'}
        report['preview_baseline']['still_ms_mean'] = round(sum(x['ms'] for x in base['stills']) / len(base['stills']))

    after = tree_hashes(source)
    report['original_episode_unchanged'] = before == after
    core.write_json(store / 'RESULT.json', report)
    core.write_json(ROOT / 'artifacts/transitions-v1/latest.json', report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    assert report['original_episode_unchanged'], 'Original episode was changed'


if __name__ == '__main__':
    main()
