"""Fixed deterministic media worker. No package installation, arbitrary shell or global DB."""
import json,os,sys,traceback
from pathlib import Path
if os.getenv('ODD_EPISODE_WORKER')!='1' or not os.getenv('EPISODE_WRITE_ROOT'):
    raise SystemExit('Production worker must be launched through verified Windows MXC')
root=Path(os.environ['EPISODE_WRITE_ROOT']).absolute()
temporary=root/'.production/temp'/os.environ['ODD_JOB_ID'];temporary.mkdir(parents=True,exist_ok=True)
for name in ('TMP','TEMP','TMPDIR'):os.environ[name]=str(temporary)
import tempfile
tempfile.tempdir=str(temporary)
sys.path.insert(0,os.environ['ODD_APP_ROOT'])
from services.api.core import read_json,write_json,update_episode
from services.api.snapshots import validate
from services.api.file_writer import EpisodeWriter
writer=EpisodeWriter(root)
job=None
try:
    validate(root,media=sys.argv[1] in ('render','draft','style-preview'))
    if sys.argv[1]=='validate':
        from services.api.media import validate_assets
        print(json.dumps(validate_assets(int(sys.argv[2]))))
    elif sys.argv[1]=='draft':
        from services.api.editor import prepare
        job=read_json(writer.path(sys.argv[2]));prepare(job['episode_id'],job['id'])
        job.update(status='COMPLETE',stage='Draft ready for review',progress=1)
        writer.json(sys.argv[2],job)
    elif sys.argv[1]=='render':
        from services.api.worker import process_job
        job=read_json(writer.path(sys.argv[2]));process_job(job)
    elif sys.argv[1]=='style-preview':
        from services.api.worker import style_preview
        print(json.dumps(style_preview(int(sys.argv[2]),sys.argv[3].split(','))))
    elif sys.argv[1]=='audio-preview':
        from services.api.media import mix_audio
        report=read_json(writer.path('reports/ASSET_VALIDATION.json'))
        if not report.get('valid'):raise ValueError('Audio preview needs validated assets; fix the Asset Manager issues first')
        mix=mix_audio(int(sys.argv[2]),report,offset_override=float(sys.argv[3]),preview=True)
        print(json.dumps(dict(gap_db=mix['measured_integrated_gap_db'],offset_db=mix['owner_music_offset_db'])))
    else:raise ValueError('Unknown fixed worker operation')
except BaseException as exc:
    if job:
        job.update(status='FAILED',error=str(exc),stage='Blocked')
        writer.json(sys.argv[2],job)
        update_episode(job['episode_id'],'FAILED',error=str(exc))
    writer.text(f'.production/logs/{os.environ.get("ODD_JOB_ID","worker")}.exception.log',traceback.format_exc())
    print(str(exc),file=sys.stderr)
    raise SystemExit(1)
