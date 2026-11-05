"""Actual parallel Windows write-denial tests. Uses only disposable sibling episodes."""
import concurrent.futures,json,os,subprocess,sys,time,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
STORE=ROOT/'artifacts/isolation-smoke'/time.strftime('%Y%m%d-%H%M%S')
os.environ['ODD_DATA_ROOT']=str(STORE)
from services.api import core,isolation,snapshots
from services.api.file_writer import EpisodeWriter,episode_lock,UnsafePath,assert_clean_tree

def main():
    core.init_db();shared=STORE/'shared';shared.mkdir(parents=True)
    (shared/'signature.wav').write_bytes(b'Disposable signature music permission canary; not usable production audio')
    (shared/'hardlink-canary.bin').write_bytes(b'unchanged')
    roots=[STORE/'episodes'/name for name in ('A','B')]
    for root in roots:root.mkdir(parents=True)
    sources=[ROOT/'prompts/00_MASTER_PROMPT.md',ROOT/'brand/skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md',ROOT/'video/remotion/src/index.tsx',shared/'signature.wav',shared/'hardlink-canary.bin']
    before={str(p):core.sha(p.read_bytes()) for p in sources}
    for root,other in [(roots[0],roots[1]),(roots[1],roots[0])]:
        snapshots.bootstrap(root)
        (root/'sibling-sentinel.txt').write_text('keep')
        p=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(root/'escape'),str(other)],capture_output=True,text=True)
        if p.returncode:raise RuntimeError('Junction fixture setup failed: '+p.stderr)
        os.link(shared/'hardlink-canary.bin',root/'hardlink-canary.bin')
        EpisodeWriter(root).json('.production/security_spec.json',dict(other=str(other),shared=str(shared),store=str(STORE),label=root.name))
    def run(root):
        # Deliberately hostile PRE-EXISTING fixtures are rejected by the production preflight.
        # Separately exercise the actual OS boundary directly to test raw junction attempts.
        rejected=False
        try:assert_clean_tree(root)
        except UnsafePath:rejected=True
        assert rejected
        result=subprocess.run(isolation.sandbox_argv(root,[sys.executable,'-B',str(ROOT/'scripts/adversarial_episode_worker.py')],network=True),
            cwd=root,env=isolation.environment(root,'parallel-security-'+root.name),capture_output=True,text=True,timeout=90)
        EpisodeWriter(root).text('.production/logs/security.stdout.log',result.stdout)
        EpisodeWriter(root).text('.production/logs/security.stderr.log',result.stderr)
        return dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(run,roots))
    reports=[]
    for root,outcome in zip(roots,outcomes):
        report=json.loads((root/'reports/SECURITY_TEST.json').read_text()) if (root/'reports/SECURITY_TEST.json').exists() else dict(verified=False,error=outcome['stderr'])
        if outcome['returncode'] or not report.get('verified'):raise RuntimeError(json.dumps(report))
        reports.append(report)
    unchanged=all(core.sha(p.read_bytes())==before[str(p)] for p in sources)
    assert unchanged
    # Same-episode conflicting writers must fail immediately; independent episode locks coexist.
    blocked=[]
    with episode_lock(roots[0],'same-episode'):
        def conflict():
            try:
                with episode_lock(roots[0],'same-episode',blocking=False):return False
            except (OSError,UnsafePath):return True
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:blocked.append(pool.submit(conflict).result())
    assert all(blocked)
    lifetime=STORE/'episodes'/'LIFETIME';lifetime.mkdir();snapshots.bootstrap(lifetime)
    token_proof=isolation.verify_boundary(lifetime)
    child_code="import os,time; from pathlib import Path; p=Path(os.environ['EPISODE_WRITE_ROOT'])/'reports/heartbeat.txt'; p.parent.mkdir(parents=True,exist_ok=True);\nwhile True: p.write_text(str(time.monotonic())); time.sleep(.1)"
    parent_code="import subprocess,sys,time; subprocess.Popen([sys.executable,'-B','-c',"+repr(child_code)+"]); time.sleep(30)"
    cancel=threading.Event();timer=threading.Timer(3,cancel.set);timer.start()
    killed=False
    try:isolation.launch(lifetime,[sys.executable,'-B','-c',parent_code],'lifetime-cancel',cancel=cancel,timeout=15)
    except isolation.IsolationError as exc:killed='cancelled' in str(exc).lower()
    finally:timer.cancel()
    heartbeat=lifetime/'reports/heartbeat.txt';assert heartbeat.exists(),'Child did not start before cancellation'
    before_heartbeat=heartbeat.read_text();time.sleep(1);assert heartbeat.read_text()==before_heartbeat
    assert killed
    result=dict(result='PASS',mechanism='Windows MXC',parallel_workers=2,preexisting_links_rejected_before_production_launch=True,shared_hashes_unchanged=unchanged,same_episode_lock_conflict_blocked=True,cancellation_kills_descendants=True,token_verified=token_proof['token_verified'],appcontainer=token_proof['appcontainer'],elevated=token_proof['elevated'],reports=reports,store=str(STORE))
    core.write_json(STORE/'RESULT.json',result);core.write_json(ROOT/'artifacts/isolation-smoke/latest.json',result)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
