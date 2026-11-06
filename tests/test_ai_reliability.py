"""Deterministic subprocesses only. No account usage, credentials or production data."""
import asyncio,json,os,runpy,sys,threading,time
from pathlib import Path
import pytest
from services.api import activity,core,creative,main,providers
from .fixtures import IDEA,SCRIPT,NARRATION,package

REAL_SPAWN=asyncio.create_subprocess_exec

def test_actual_worker_consumes_partial_jsonl_and_stderr_before_exit(tmp_path,monkeypatch):
    root=tmp_path;folder=root/'.production/runs/fake';folder.mkdir(parents=True)
    spec=dict(job_id='fake',provider='codex_cli',auth_home=str(root/'fake-auth'),command='not-a-live-cli',messages=[dict(role='user',content='fixture')],schema={'type':'object'},activity=dict(job_id='fake',episode_id=1,stage='prepare'))
    (folder/'cli_request.json').write_text(json.dumps(spec))
    monkeypatch.setenv('EPISODE_WRITE_ROOT',str(root));monkeypatch.setenv('ODD_JOB_ID','fake');monkeypatch.setenv('ODD_APP_ROOT',str(core.ROOT))
    monkeypatch.setattr(sys,'argv',['cli_worker.py','.production/runs/fake/cli_request.json'])
    response=str(folder/'response.json');barrier=str(root/'seen-before-exit')
    code=f'''import sys,time,json,pathlib
sys.stdout.write('{{"type":"thread.');sys.stdout.flush();time.sleep(.1)
sys.stdout.write('started"}}\\n');sys.stdout.flush()
print('malformed event',flush=True)
print(json.dumps({{"type":"turn.started"}}),flush=True)
sys.stderr.write('diagnostic'*40000);sys.stderr.flush()
deadline=time.monotonic()+10
while not pathlib.Path({barrier!r}).exists() and time.monotonic()<deadline:time.sleep(.05)
assert pathlib.Path({barrier!r}).exists()
pathlib.Path({response!r}).write_text(json.dumps({{"fixture":"valid Unicode café"}}))
print(json.dumps({{"type":"turn.completed"}}),flush=True)
'''
    async def fake_spawn(*args,**kwargs):
        return await REAL_SPAWN(sys.executable,'-u','-c',code,**kwargs)
    monkeypatch.setattr(asyncio,'create_subprocess_exec',fake_spawn)
    observed=[]
    def witness():
        end=time.monotonic()+10
        while time.monotonic()<end:
            p=root/'.production/activity/fake.json'
            if p.exists():
                events=core.read_json(p)['events']
                if any(e['message']=='Provider is generating the structured response' for e in events):
                    observed.extend(events);Path(barrier).touch();return
            time.sleep(.05)
    thread=threading.Thread(target=witness);thread.start()
    runpy.run_path(str(core.ROOT/'scripts/cli_worker.py'),run_name='__main__');thread.join()
    assert observed and not any(e['type']=='ai.completed' for e in observed)
    events=core.read_json(root/'.production/activity/fake.json')['events']
    assert [e['sequence'] for e in events]==list(range(1,len(events)+1))
    assert events[-1]['type']=='output.parsed'
    assert (folder/'provider.stderr.log').stat().st_size<=256*1024
    assert 'café' not in json.dumps(events,ensure_ascii=False)

@pytest.mark.parametrize('error,code',[
 ('NOT_INSTALLED: executable missing','NOT_INSTALLED'),('401 authentication required','AUTHENTICATION'),
 ('TIMEOUT: Worker timeout after 300s','TIMEOUT'),('PROCESS_EXIT: exited unsuccessfully','PROCESS_EXIT'),
 ('rate limit 429','RATE_LIMIT'),('INVALID_OUTPUT: invalid JSON','INVALID_OUTPUT'),
 ('INVALID_OUTPUT: empty provider response','INVALID_OUTPUT'),('INVALID_OUTPUT: truncated JSON','INVALID_OUTPUT'),
 ('Generation cancelled','CANCELLED'),('ARTIFACT_PERSISTENCE: disk denied','ARTIFACT_PERSISTENCE'),
 ('PROCESS_SPAWN: unavailable executable','PROCESS_SPAWN'),('NETWORK: connection reset','NETWORK')])
def test_failures_persist_safe_exact_diagnoses(store,error,code):
    ep=creative.create_episode(IDEA);run=creative.start_task('script',dict(idea=IDEA),ep['id'])
    creative.run_progress(run['run_id'],'Waiting for model response',0,status='RUNNING')
    creative.fail_run(run['run_id'],error+' PRIVATE fixture value')
    row=next(r for r in main.runs() if r['id']==run['run_id'])
    assert row['failure']['category']==code and row['failure']['failed_stage']=='Waiting for model response'
    assert row['failure']['failed_at'] and row['failure']['elapsed_seconds']>=0
    assert 'PRIVATE' not in row['error']
    private=core.read_json(core.epdir(ep)/f'.production/runs/{run["run_id"]}/failure.json')
    assert 'PRIVATE' in private['technical']

def test_retry_clears_current_error_preserves_history_and_approval(store):
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    first=creative.approve(ep['id'],NARRATION);approved=core.episode(ep['id'])['data']['approval']
    creative.fail_run(first['run_id'],'TIMEOUT: Worker timeout after 300s')
    retry=main.retry_generation(first['run_id']);current=core.episode(ep['id'])
    assert main.retry_generation(first['run_id'])['run_id']==retry['run_id']
    assert current['data']['error'] is None and current['data']['approval']==approved
    rows=main.runs();new=next(r for r in rows if r['id']==retry['run_id']);old=next(r for r in rows if r['id']==first['run_id'])
    assert new['attempt_number']==2 and new['job_group_id']==first['run_id'] and new['error'] is None
    assert old['failure']['category']=='TIMEOUT'
    creative.complete_run(retry['run_id'],package(),manual=True)
    assert core.episode(ep['id'])['data']['error'] is None
    with pytest.raises(ValueError,match='already exists'):main.retry_generation(first['run_id'])

def test_three_episode_activity_and_attempt_isolation(store):
    ids=[]
    for i in range(3):
        ep=creative.create_episode({**IDEA,'title':f'Isolated QA {i}'})
        run=creative.start_task('script',dict(idea=IDEA),ep['id']);ids.append(run['run_id'])
        creative.run_event(run['run_id'],'request.sent','Complete request delivered to CLI input')
        jobs=activity.collect(ep['id']);assert {j['job_id'] for j in jobs}=={run['run_id']}
        assert jobs[0]['generation_progress']['request_sent']
    assert len(set(ids))==3

def test_running_does_not_mean_request_sent_and_legacy_events_are_recognized(tmp_path):
    activity.emit(tmp_path,'qa',1,'codex_cli','prepare','job.started','Starting')
    p=activity.generation_progress(tmp_path,'qa','RUNNING','Checking authentication','codex_cli')
    assert not p['request_sent'] and p['phase']=='preflight'
    activity.emit(tmp_path,'qa',1,'codex_cli','prepare','ai.activity','Provider session established')
    p=activity.generation_progress(tmp_path,'qa','RUNNING','Checking authentication','codex_cli')
    assert p['request_sent'] and p['phase']=='connected'

@pytest.mark.parametrize('mode',['exit','quota','rate','empty','invalid','truncated','interrupted','large'])
def test_real_fake_cli_failure_paths(tmp_path,monkeypatch,mode):
    folder=tmp_path/'.production/runs/fake';folder.mkdir(parents=True)
    spec=dict(job_id='fake',provider='codex_cli',auth_home=str(tmp_path/'fake-auth'),command='not-a-live-cli',messages=[dict(role='user',content='fixture')],schema={'type':'object'},activity=dict(job_id='fake',episode_id=1,stage='prepare'))
    (folder/'cli_request.json').write_text(json.dumps(spec))
    for key,value in dict(EPISODE_WRITE_ROOT=str(tmp_path),ODD_JOB_ID='fake',ODD_APP_ROOT=str(core.ROOT)).items():monkeypatch.setenv(key,value)
    monkeypatch.setattr(sys,'argv',['cli_worker.py','.production/runs/fake/cli_request.json'])
    code="import sys,json,pathlib\n"
    if mode=='exit':code+='sys.exit(7)'
    elif mode=='large':code+="print('x'*(5*1024*1024),flush=True)"
    elif mode in ('quota','rate'):code+='print(json.dumps({"type":"turn.failed","error":{"message":'+repr('quota exhausted' if mode=='quota' else 'rate limit 429')+'}}),flush=True)'
    elif mode=='interrupted':code+='print(json.dumps({"type":"item.completed","item":{"type":"command_execution"}}),flush=True); import time;time.sleep(30)'
    elif mode in ('invalid','truncated'):code+='pathlib.Path('+repr(str(folder/'response.json'))+').write_text('+repr('not JSON' if mode=='invalid' else '{"partial":')+')'
    processes=[]
    async def fake_spawn(*args,**kwargs):
        proc=await REAL_SPAWN(sys.executable,'-u','-c',code,**kwargs);processes.append(proc);return proc
    monkeypatch.setattr(asyncio,'create_subprocess_exec',fake_spawn)
    with pytest.raises((ValueError,SystemExit)):
        runpy.run_path(str(core.ROOT/'scripts/cli_worker.py'),run_name='__main__')
    assert processes[0].returncode is not None
    events=core.read_json(tmp_path/'.production/activity/fake.json')['events']
    assert not any(e['type']=='job.completed' for e in events)

def test_process_heartbeat_is_not_provider_output_progress(tmp_path):
    activity.emit(tmp_path,'qa',1,'codex_cli','prepare','ai.activity','Provider session established')
    before=activity.generation_progress(tmp_path,'qa','RUNNING','','codex_cli')
    activity.emit(tmp_path,'qa',1,'codex_cli','prepare','process.alive','CLI process is running; this is not model-output progress')
    after=activity.generation_progress(tmp_path,'qa','RUNNING','','codex_cli')
    assert after['last_provider_event_at']==before['last_provider_event_at']
    assert after['last_process_check_at'] and after['last_event_at']==before['last_event_at']

def test_completed_package_is_not_labeled_as_ideas(tmp_path):
    summary=activity.generation_progress(tmp_path,'qa','SUCCEEDED','','codex_cli','prepare')
    assert summary['message']=='Production package validated and saved'

def test_late_failure_cannot_overwrite_new_attempt_state(store):
    ep=creative.create_episode(IDEA);first=creative.start_task('script',dict(idea=IDEA),ep['id'])
    creative.fail_run(first['run_id'],'TIMEOUT: deadline')
    retry=main.retry_generation(first['run_id']);before=core.episode(ep['id'])
    creative.fail_run(first['run_id'],'TIMEOUT: delayed old failure')
    after=core.episode(ep['id'])
    assert after['status']==before['status'] and after['data']['error'] is None
    assert after['data']['pending_run']==retry['run_id']

def test_automatic_retry_registration_prevents_competing_jobs(store,monkeypatch):
    ep=creative.create_episode(IDEA);first=creative.start_task('script',dict(idea=IDEA),ep['id']);creative.fail_run(first['run_id'],'TIMEOUT: deadline')
    main.put_settings({'provider':'codex_cli'})
    monkeypatch.setattr(creative._executor,'submit',lambda *args:None)
    monkeypatch.setattr(creative,'_cancellations',{})
    retry=main.retry_generation(first['run_id'])
    assert retry['status']=='QUEUED' and retry['attempt_number']==2
    with pytest.raises(ValueError,match='already active'):main.retry_generation(first['run_id'])
    assert len(main.runs())==2

def test_artifact_failure_is_persisted_without_changing_approved_script(store,monkeypatch):
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    run=creative.approve(ep['id'],NARRATION)
    monkeypatch.setattr(providers,'generate',lambda *args,**kwargs:package())
    def denied(*args):raise OSError('Synthetic disk permission failure')
    monkeypatch.setattr(creative,'populate',denied)
    result=creative.execute_run(run['run_id'],core.settings(),[],creative.TASKS['prepare'][1].model_json_schema(),core.epdir(ep),background=True)
    assert result['status']=='FAILED'
    row=next(r for r in main.runs() if r['id']==run['run_id'])
    assert row['failure']['category']=='ARTIFACT_PERSISTENCE'
    assert core.episode(ep['id'])['data']['script']['narration']==NARRATION
