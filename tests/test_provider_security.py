import copy,json,os,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from services.api import core,creative,skills,snapshots,providers,isolation,main
from services.api.file_writer import EpisodeWriter,UnsafePath,episode_lock,assert_clean_tree
from tests.fixtures import IDEA,SCRIPT,NARRATION,package

@pytest.mark.parametrize('relative',['../escape.txt','05_assets/../../escape','C:\\escape','/absolute','\\\\host\\share\\file','filename:stream','CON','reports/../escape','reports//empty.txt'])
def test_central_writer_rejects_paths(store,relative):
    ep=creative.create_episode(IDEA);writer=EpisodeWriter(creative.epdir(ep))
    with pytest.raises(UnsafePath):writer.text(relative,'forbidden')

def test_writer_pins_immutable_content_and_atomic_outputs(store):
    ep=creative.create_episode(IDEA);root=creative.epdir(ep);writer=EpisodeWriter(root)
    with pytest.raises(UnsafePath):writer.text('.production/input_snapshot/prompts/00_MASTER_PROMPT.md','replace')
    writer.text('reports/safe.txt','one');writer.text('reports/safe.txt','two')
    assert (root/'reports/safe.txt').read_text()=='two'
    assert not list(root.glob('reports/*.tmp'))

def test_hardlink_is_rejected_before_execution(store):
    ep=creative.create_episode(IDEA);root=creative.epdir(ep)
    source=store/'shared-canary.txt';source.write_text('read only')
    os.link(source,root/'hardlink.txt')
    with pytest.raises(UnsafePath):assert_clean_tree(root)
    with pytest.raises(UnsafePath):EpisodeWriter(root).text('hardlink.txt','write')
    assert source.read_text()=='read only'

def test_same_episode_lock_and_distinct_episode_concurrency(store):
    a=creative.epdir(creative.create_episode(IDEA));b=creative.epdir(creative.create_episode({**IDEA,'title':'Other independent episode'}))
    with episode_lock(a,'conflict'):
        def try_a():
            with pytest.raises(UnsafePath):
                with episode_lock(a,'conflict',blocking=False):pass
        def write_b():
            with episode_lock(b,'conflict',blocking=False):EpisodeWriter(b).text('reports/safe.txt','episode B')
        with ThreadPoolExecutor(max_workers=2) as pool:
            pool.submit(try_a).result();pool.submit(write_b).result()
    assert (b/'reports/safe.txt').read_text()=='episode B'

def test_global_skill_changes_do_not_repin_existing_episode(store,monkeypatch):
    ep=creative.create_episode(IDEA);root=creative.epdir(ep);pinned=snapshots.source_root(root)
    before=skills.model_request('02_SCRIPT_WRITING.md',{},core.settings(),root=pinned)[1]
    global_docs,global_rules=skills.load_skills()
    altered=copy.deepcopy(global_docs);altered[0]['sha256']='changed global hash'
    original=skills.load_skills
    monkeypatch.setattr(creative,'load_skills',lambda source=core.ROOT:(altered,global_rules) if source==core.ROOT else original(source))
    core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    run=creative.approve(ep['id'],NARRATION)
    creative.complete_run(run['run_id'],package(),manual=True)
    after=skills.model_request('02_SCRIPT_WRITING.md',{},core.settings(),root=pinned)[1]
    assert before['skills'][0]['sha256']==after['skills'][0]['sha256']
    assert core.episode(ep['id'])['status']=='AWAITING_ASSETS'

def test_worker_cannot_open_global_database(store,monkeypatch):
    ep=creative.create_episode(IDEA);root=creative.epdir(ep)
    monkeypatch.setenv('ODD_EPISODE_WORKER','1');monkeypatch.setenv('EPISODE_WRITE_ROOT',str(root))
    with pytest.raises(PermissionError):
        with core.db():pass
    with pytest.raises(UnsafePath):core.textfile(store/'outside.txt','forbidden')
    core.update_episode(ep['id'],'TEST_PROGRESS',message='Local worker state only')
    assert core.read_json(root/'production_status.json')['status']=='TEST_PROGRESS'

def test_codex_schema_and_error_classification():
    schema=providers.strict_schema({'type':'object','properties':{'value':{'type':'string','default':'x'}}})
    assert schema['required']==['value'] and schema['additionalProperties'] is False
    for text,code in [('429 rate limit exceeded','USAGE_LIMIT'),('not logged in','AUTHENTICATION'),('timeout','TIMEOUT'),('invalid JSON schema','INVALID_OUTPUT')]:assert providers.classify(text)==code

def test_unverified_boundary_never_launches_cli(store,monkeypatch):
    ep=creative.create_episode(IDEA)
    monkeypatch.setattr(providers,'cli_info',lambda p:dict(installed=True,eligible=True,command='codex.exe'))
    monkeypatch.setattr(isolation,'require_verified',lambda root:(_ for _ in ()).throw(isolation.IsolationError('Native isolation unavailable')))
    called=[]
    monkeypatch.setattr(isolation.subprocess,'Popen',lambda *a,**k:called.append(a))
    with pytest.raises(providers.ProviderError):providers.generate({**core.settings(),'provider':'codex_cli'},[],{},creative.epdir(ep),'blocked')
    assert called==[]
    assert not list(creative.epdir(ep).glob('.production/runtime/codex-auth/*/auth.json'))

def test_controller_api_rejects_unauthorized_worker_mutations(store,monkeypatch):
    monkeypatch.setattr(main,'start_worker',lambda:SimpleNamespace(join=lambda timeout:None))
    with TestClient(main.app) as client:
        assert client.post('/api/episodes',json=IDEA).status_code==401
        client.headers['X-Odd-Controller']=core.controller_token()
        assert client.post('/api/episodes',json=IDEA).status_code==200
        for provider in providers.PROVIDERS:
            assert client.put('/api/settings',json={'provider':provider}).status_code==200

def test_claude_subscription_not_used_for_dashboard_automation(store,monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY',raising=False)
    ep=creative.create_episode(IDEA)
    monkeypatch.setattr(providers,'cli_info',lambda provider:dict(installed=True,eligible=False,auth_method='claude.ai',eligibility_message='Supported API authentication required; use manual Claude Code'))
    with pytest.raises(providers.ProviderError,match='Supported API authentication'):
        providers.generate({**core.settings(),'provider':'claude_cli'},[],{},creative.epdir(ep),'claude-test')

def test_signature_music_is_pinned_across_global_updates(store,monkeypatch):
    source=store/'signature.wav';source.write_bytes(b'Synthetic music pin version one')
    monkeypatch.setenv('ODD_SIGNATURE_MUSIC',str(source));monkeypatch.setenv('ODD_SIGNATURE_MUSIC_VERSION','test-v1')
    first=creative.epdir(creative.create_episode(IDEA));old=snapshots.validate(first)['signature_music']['sha256']
    source.write_bytes(b'Synthetic music pin version two')
    monkeypatch.setenv('ODD_SIGNATURE_MUSIC_VERSION','test-v2')
    second=creative.epdir(creative.create_episode({**IDEA,'title':'New signature version'}))
    assert snapshots.validate(first)['signature_music']['sha256']==old
    assert core.sha((first/'05_assets/music/signature.wav').read_bytes())==old
    assert snapshots.validate(second)['signature_music']['sha256']!=old

def test_private_runtime_files_are_not_served_by_dashboard(store,monkeypatch):
    ep=creative.create_episode(IDEA);root=creative.epdir(ep)
    EpisodeWriter(root).text('.production/runtime/private-canary.txt','Synthetic private-runtime canary, no credentials')
    monkeypatch.setattr(main,'start_worker',lambda:SimpleNamespace(join=lambda timeout:None))
    with TestClient(main.app) as client:
        assert client.get(f'/api/episodes/{ep["id"]}/file/.production/runtime/private-canary.txt').status_code==404
        detail=client.get(f'/api/episodes/{ep["id"]}').json()
        assert all('.production' not in path for path in detail['files'])

def test_concurrent_preparation_commits_do_not_interleave(store):
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    first=creative.approve(ep['id'],NARRATION)
    current=core.episode(ep['id'])
    second=creative.start_task('prepare',dict(idea=IDEA,approved_narration=NARRATION,approval=current['data']['approval']),ep['id'])
    one=package();two=copy.deepcopy(one);two['scenes'][0]['beat']+=' A distinct alternative staging direction.'
    def commit(pair):
        run,payload=pair
        try:creative.complete_run(run['run_id'],payload,manual=True);return 'committed'
        except ValueError:return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as executor:outcomes=list(executor.map(commit,[(first,one),(second,two)]))
    assert sorted(outcomes)==['committed','rejected']
    final=core.episode(ep['id']);root=creative.epdir(final)
    beat=final['data']['package']['scenes'][0]['beat']
    assert beat in core.read_json(root/'04_google_flow/IMAGE_JOBS.json')['jobs'][0]['prompt']
    assert beat in (root/'03_storyboard/STORYBOARD.md').read_text(encoding='utf-8')
    assert final['data']['approval']['sha256']==core.sha(NARRATION)

def run_claude_worker(tmp_path,monkeypatch,mode,env_name,secret):
    import asyncio,json,runpy,subprocess,sys,types
    root=tmp_path/'episode';root.mkdir()
    for name in ('TMP','TEMP','TMPDIR'):monkeypatch.setenv(name,str(tmp_path))
    for name in ('ANTHROPIC_API_KEY','CLAUDE_CODE_OAUTH_TOKEN'):monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('EPISODE_WRITE_ROOT',str(root));monkeypatch.setenv('ODD_JOB_ID','job');monkeypatch.setenv('ODD_APP_ROOT',str(providers.ROOT))
    monkeypatch.setenv(env_name,secret)
    relative='.production/runs/job/cli_request.json'
    spec=dict(provider='claude_cli',command='claude.exe',model='',messages=[dict(role='user',content='hi')],schema={'type':'object'},job_id='job',auth_home=None,claude_auth=mode)
    path=root/relative;path.parent.mkdir(parents=True);path.write_text(json.dumps(spec),encoding='utf-8')
    calls={}
    def fake_run(args,**kwargs):
        calls.update(args=args,env=kwargs['env'])
        return types.SimpleNamespace(returncode=0,stdout=json.dumps(dict(structured_output=dict(ok=True))),stderr='')
    monkeypatch.setattr(subprocess,'run',fake_run);monkeypatch.setattr(sys,'argv',['cli_worker.py',relative])
    class Input:
        def write(self,data):pass
        async def drain(self):pass
        def close(self):pass
    class Output:
        sent=False
        async def readline(self):
            if self.sent:return b''
            self.sent=True
            return json.dumps(dict(type='result',structured_output=dict(ok=True))).encode()+b'\n'
    async def fake_async(*args,**kwargs):
        calls.update(args=list(args),env=kwargs['env'])
        async def wait():return 0
        return types.SimpleNamespace(returncode=0,stdin=Input(),stdout=Output(),wait=wait)
    monkeypatch.setattr(asyncio,'create_subprocess_exec',fake_async)
    monkeypatch.setattr(sys,'path',list(sys.path))
    runpy.run_path(str(providers.ROOT/'scripts/cli_worker.py'),run_name='__main__')
    recorded=(root/'.production/runs/job/invocation.json').read_text(encoding='utf-8')+path.read_text(encoding='utf-8')
    assert secret not in recorded
    return calls,root

def test_claude_subscription_token_runs_without_bare_or_host_config(tmp_path,monkeypatch):
    calls,root=run_claude_worker(tmp_path,monkeypatch,'subscription_token','CLAUDE_CODE_OAUTH_TOKEN','oauth-secret')
    assert '--bare' not in calls['args'] and calls['args'][1:3]==['--setting-sources','']
    assert calls['args'][calls['args'].index('--tools')+1]=='' and '--strict-mcp-config' in calls['args']
    assert calls['env']['CLAUDE_CONFIG_DIR'].startswith(str(root))
    assert calls['env']['CLAUDE_CODE_OAUTH_TOKEN']=='oauth-secret'

def test_claude_api_key_keeps_bare_mode(tmp_path,monkeypatch):
    calls,_=run_claude_worker(tmp_path,monkeypatch,'api_key','ANTHROPIC_API_KEY','key-secret')
    assert calls['args'][1]=='--bare' and 'CLAUDE_CONFIG_DIR' not in calls['env']

def test_claude_auth_mode_prefers_explicit_api_key(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY',raising=False);monkeypatch.delenv('CLAUDE_CODE_OAUTH_TOKEN',raising=False)
    assert providers.claude_auth_mode() is None
    monkeypatch.setenv('CLAUDE_CODE_OAUTH_TOKEN','t');assert providers.claude_auth_mode()=='subscription_token'
    monkeypatch.setenv('ANTHROPIC_API_KEY','k');assert providers.claude_auth_mode()=='api_key'

def test_subscription_token_only_reaches_workers_that_request_it(tmp_path,monkeypatch):
    from services.api import isolation
    monkeypatch.setenv('CLAUDE_CODE_OAUTH_TOKEN','oauth-secret')
    assert 'CLAUDE_CODE_OAUTH_TOKEN' not in isolation.environment(tmp_path,'render')
    assert isolation.environment(tmp_path,'ai',{'CLAUDE_CODE_OAUTH_TOKEN':'oauth-secret'})['CLAUDE_CODE_OAUTH_TOKEN']=='oauth-secret'
    assert 'oauth-secret' not in providers.redact('failed oauth-secret')
