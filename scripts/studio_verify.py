"""Explicit real-media / real-provider checks. No usage unless --provider is supplied."""
import argparse,json,os,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser()
parser.add_argument('--prepare-real',action='store_true')
parser.add_argument('--render',action='store_true')
parser.add_argument('--cinematic',action='store_true',help='Explicitly adopt the cinematic profile on the disposable copy only')
parser.add_argument('--provider',choices=['codex_cli','claude_cli'])
parser.add_argument('--resume-store',type=Path)
args=parser.parse_args()
if args.resume_store:
    store=args.resume_store.resolve()
    if not store.is_relative_to((ROOT/'artifacts/studio-upgrade').resolve()) or not store.is_dir():raise ValueError('Resume only a disposable studio verification store')
else:
    store=ROOT/'artifacts/studio-upgrade'/time.strftime('run-%Y%m%d-%H%M%S');store.mkdir(parents=True,exist_ok=False)
os.environ.update(ODD_DATA_ROOT=str(store),ODD_AI_PROVIDER='manual',ODD_TEST_RUN='1')
from services.api import core,worker,editor,providers,isolation

def main():
    core.init_db();report=dict(store=str(store),at=core.now(),provider_test='not requested',native_draft='not requested')
    if args.prepare_real:
        source=ROOT/'episodes/OF_R001_the-key-was-outside';dest=store/'episodes'/source.name
        before={p.relative_to(source).as_posix():core.sha(p.read_bytes()) for p in source.rglob('*') if p.is_file() and '.production/runtime' not in p.as_posix()}
        dest.mkdir(parents=True)
        for name in ['00_brief','01_script','02_characters','03_storyboard','04_google_flow','05_assets']:
            shutil.copytree(source/name,dest/name)
        for name in ['episode.json','production_status.json']:
            shutil.copy2(source/name,dest/name)
        (dest/'.production').mkdir()
        (dest/'07_export/final').mkdir(parents=True)
        shutil.copytree(source/'.production/input_snapshot',dest/'.production/input_snapshot')
        shutil.copy2(source/'.production/provenance.json',dest/'.production/provenance.json')
        original=core.read_json(dest/'episode.json')
        # Register the copied identity only in this disposable controller index.
        with core.db() as c:c.execute('INSERT INTO episodes(id,code,path,title,status,data,updated) VALUES (?,?,?,?,?,?,?)',
            (original['id'],original['code'],original['path'],original['title'],original['status'],json.dumps(original['data']),original['updated']))
        core.update_episode(original['id'],'AWAITING_ASSETS',exports=[],error=None)
        if args.cinematic:
            from services.api import styles
            adopted=styles.pin_style_upgrade(dest)
            core.update_episode(original['id'],style=adopted)
            report['disposable_copy_explicit_style_adoption']=styles.FLOW_ID
        started=time.perf_counter();jid=worker.enqueue(original['id'],'draft')
        with core.db() as c:job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
        worker.run_isolated_render(job)
        draft=editor.load(original['id'])
        report.update(native_draft='PASS',draft_seconds=round(time.perf_counter()-started,3),episode_id=original['id'],
            scenes=len(draft['timeline']['scenes']),captions=len(draft['timeline']['captions']),frames=draft['timeline']['durationInFrames'],
            no_mp4_before_render=not bool(list(dest.rglob('*.mp4'))),isolation=isolation.status(dest))
        if args.render:
            jid=worker.enqueue(original['id'],'render')
            with core.db() as c:job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
            started=time.perf_counter();worker.run_isolated_render(job)
            report.update(render_seconds=round(time.perf_counter()-started,3),qc=core.read_json(dest/'07_export/QC_REPORT.json'))
        assert all((source/p).is_file() and core.sha((source/p).read_bytes())==digest for p,digest in before.items()),'Original episode was changed'
        report['original_episode_unchanged']=True
    if args.provider:
        report['provider_test']=providers.test_connection(args.provider)
        report['provider_test'].pop('workspace',None)
    if args.render and not args.prepare_real:
        jid=worker.enqueue(1,'render')
        with core.db() as c:job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
        started=time.perf_counter();worker.run_isolated_render(job)
        report.update(render_seconds=round(time.perf_counter()-started,3),qc=core.read_json(core.epdir(core.episode(1))/'07_export/QC_REPORT.json'))
    core.write_json(store/'RESULT.json',report);core.write_json(ROOT/'artifacts/studio-upgrade/latest.json',report)
    if args.prepare_real:core.write_json(ROOT/'artifacts/studio-upgrade/latest-draft.json',report)
    if args.provider:core.write_json(ROOT/f'artifacts/studio-upgrade/latest-{args.provider}.json',report)
    if args.render:core.write_json(ROOT/'artifacts/studio-upgrade/latest-render.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
