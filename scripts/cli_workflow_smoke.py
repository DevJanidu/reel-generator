"""Real CLI integration test using an isolated disposable application store."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
STORE=ROOT/'artifacts/cli-workflow'/time.strftime('%Y%m%d-%H%M%S')
STORE.mkdir(parents=True,exist_ok=False)
env={**os.environ,'ODD_DATA_ROOT':str(STORE),'ODD_PORT':'8126','ODD_AI_PROVIDER':'codex_cli','ODD_TEST_RUN':'1'}
import httpx
def main():
    logfile=(STORE/'controller.log').open('w',encoding='utf-8')
    server=subprocess.Popen([sys.executable,'-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8126'],cwd=ROOT,env=env,stdout=logfile,stderr=logfile)
    try:
        with httpx.Client(base_url='http://127.0.0.1:8126',timeout=90) as client:
            for _ in range(100):
                try:
                    if client.get('/api/status').is_success:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            client.headers['X-Odd-Controller']=json.loads((STORE/'data/controller-access.json').read_text())['token']
            def post(path,data=None):
                r=client.post(path,json=data);r.raise_for_status();return r.json()
            def waitrun(runid):
                last='';deadline=time.monotonic()+500
                while time.monotonic()<deadline:
                    r=client.get('/api/runs/'+runid+'/result').json()
                    msg=r['status']+' '+str(r['stage'])
                    if msg!=last:print(msg,flush=True);last=msg
                    if r['status']=='SUCCEEDED':return r['result']
                    if r['status'] in ('FAILED','CANCELLED'):raise RuntimeError(r.get('error'))
                    time.sleep(2)
                raise TimeoutError(runid)
            start=post('/api/ideas/generate',{'direction':'Engineering verification: varied original stories for ODD FRAME. Keep the selected story a compact complete mystery around 45 seconds; never pad.'})
            ideas=waitrun(start['run_id']);assert len(ideas['ideas'])==10
            ep=post('/api/episodes',ideas['ideas'][0]);eid=ep['id'];prefix=f'/api/episodes/{eid}'
            print('Selected real CLI-generated idea: '+ep['code']+' '+ep['title'],flush=True)
            run=post(prefix+'/script');waitrun(run['run_id'])
            deadline=time.monotonic()+500;last=''
            while time.monotonic()<deadline:
                ep=client.get(prefix).json()
                if ep['status']!=last:print('EPISODE '+ep['status'],flush=True);last=ep['status']
                if ep['status']=='AWAITING_APPROVAL':break
                if ep['status']=='FAILED':raise RuntimeError(ep['data'].get('error'))
                time.sleep(2)
            else:raise TimeoutError('Script review')
            frozen=ep['data']['script']['narration']
            run=post(prefix+'/approve',{'narration':frozen,'brief':ep['data']['script']['brief']})
            waitrun(run['run_id'])
            ep=client.get(prefix).json();assert ep['status']=='AWAITING_ASSETS',ep['status']
            directory=STORE/ep['path']
            required=['01_script/narration.txt','01_script/SCRIPT_APPROVAL.json','02_characters/CHARACTER_BIBLE.md','02_characters/CONTINUITY_MATRIX.md','03_storyboard/STORYBOARD.md','03_storyboard/RETENTION_AUDIT.md','04_google_flow/IMAGE_JOBS.json','reports/SKILL_PROVENANCE.json']
            assert all((directory/p).stat().st_size>0 for p in required)
            assert (directory/'01_script/narration.txt').read_text(encoding='utf-8')==frozen
            flow=json.loads((directory/'04_google_flow/IMAGE_JOBS.json').read_text(encoding='utf-8'))
            assert all(j['type']=='image' for j in flow['jobs'])
            proof=json.loads((directory/'reports/SKILL_PROVENANCE.json').read_text(encoding='utf-8'))
            assert all(len(r['skills'])==4 and r['full_read_validated'] for r in proof['runs'])
            assert not list(directory.glob('.production/runtime/codex-auth/*/auth.json'))
            result=dict(result='PASS',provider='codex_cli',live_cli=True,episode=ep['code'],title=ep['title'],workspace=str(directory),idea_count=10,scene_count=len(flow['jobs']),script_approval_count=1,approved_narration_unchanged=True,required_files=required,ready_state=ep['status'],isolation=ep['isolation'],credential_cache_retained=False,limitations=['Disposable test-harness approval, not an owner production release','No user images/audio were generated or rendered in this test'])
            (STORE/'RESULT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            (ROOT/'artifacts/cli-workflow/latest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps(result,indent=2),flush=True)
    finally:
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill()
        logfile.close()
if __name__=='__main__':main()
