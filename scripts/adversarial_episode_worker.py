"""Security test payload: intentionally hostile writes under the actual worker token."""
import json,os,subprocess,sys,time
from pathlib import Path
root=Path(os.environ['EPISODE_WRITE_ROOT']);app=Path(os.environ['ODD_APP_ROOT'])
sys.path.insert(0,str(app))
from services.api.file_writer import EpisodeWriter,episode_lock
spec=json.loads((root/'.production/security_spec.json').read_text())
other=Path(spec['other']);shared=Path(spec['shared']);checks=[]
def attempt(name,fn):
    try:fn();checks.append(dict(name=name,blocked=False))
    except (OSError,ValueError) as exc:checks.append(dict(name=name,blocked=True,error=type(exc).__name__))
def writable(path):
    with path.open('r+b'):pass
for relative in ['prompts/00_MASTER_PROMPT.md','brand/skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md','video/remotion/src/index.tsx']:
    attempt('modify '+relative,lambda p=app/relative:writable(p))
attempt('shared signature instrumental',lambda:writable(shared/'signature.wav'))
attempt('write repository root',lambda:(app/'FORBIDDEN_EPISODE_WRITE.txt').write_text('forbidden'))
attempt('write other episode',lambda:(other/'FORBIDDEN_EPISODE_WRITE.txt').write_text('forbidden'))
attempt('raw ../ traversal',lambda:(root/'..'/'FORBIDDEN_EPISODE_WRITE.txt').write_text('forbidden'))
attempt('absolute outside path',lambda:(shared/'FORBIDDEN_EPISODE_WRITE.txt').write_text('forbidden'))
attempt('junction escape',lambda:(root/'escape'/'FORBIDDEN_EPISODE_WRITE.txt').write_text('forbidden'))
def create_hardlink():
    link=root/'worker-created-hardlink.bin'
    os.link(shared/'hardlink-canary.bin',link)
    writable(link)
attempt('create hardlink escape',create_hardlink)
attempt('immutable master snapshot',lambda:writable(root/'.production/input_snapshot/prompts/00_MASTER_PROMPT.md'))
attempt('rename immutable snapshot directory',lambda:(root/'.production/input_snapshot').rename(root/'.production/temp/stolen-snapshot'))
attempt('rename immutable provenance',lambda:(root/'.production/provenance.json').rename(root/'.production/temp/stolen-provenance.json'))
attempt('write shared cache',lambda:(app/'data'/'FORBIDDEN_CACHE.txt').write_text('forbidden'))
attempt('delete sibling episode sentinel',lambda:(other/'sibling-sentinel.txt').unlink())
attempt('rename sibling episode',lambda:other.rename(other.with_name('FORBIDDEN_RENAME')))
attempt('read controller capability',lambda:(Path(spec['store'])/'data/controller-access.json').read_bytes())
child=subprocess.run([sys.executable,'-B','-c',"from pathlib import Path; import sys; Path(sys.argv[1]).write_text('forbidden')",str(other/'FORBIDDEN_CHILD_WRITE.txt')],capture_output=True)
checks.append(dict(name='inherited child process write',blocked=child.returncode!=0))
writer=EpisodeWriter(root)
for name in ['../outside.txt',str(other/'absolute.txt'),'escape/writer.txt','05_assets/../../outside.txt','C:\\outside.txt','\\\\server\\share\\outside.txt']:
    attempt('writer rejects '+name,lambda n=name:writer.text(n,'forbidden'))
writer.text('reports/authorized.txt','authorized '+spec['label'])
writer.json('07_export/final/isolated-test-output.json',dict(episode=spec['label'],sources=['narration','instrumental'],sfx=False))
with episode_lock(root,'concurrent-proof'):
    writer.text('.production/logs/concurrency.log','per-episode lock held');time.sleep(.5)
report=dict(verified=all(c['blocked'] for c in checks),checks=checks,own_write=(root/'reports/authorized.txt').is_file(),label=spec['label'])
writer.json('reports/SECURITY_TEST.json',report)
print(json.dumps(report))
sys.exit(0 if report['verified'] and report['own_write'] else 5)
