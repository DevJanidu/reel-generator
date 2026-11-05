import copy
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from services.api import core,creative,skills,media,worker,main
from services.api.models import Flow,Package
from .fixtures import IDEA,SCRIPT,NARRATION,package

def prepared():
    ep=creative.create_episode(IDEA)
    core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    run=creative.approve(ep['id'],NARRATION)
    creative.complete_run(run['run_id'],package(),manual=True)
    return core.episode(ep['id'])

def test_all_full_documents_and_source_preservation():
    docs,rules=skills.load_skills()
    assert len(docs)==4
    for d in docs:
        assert d['text'].encode()==(core.ROOT/d['canonical_path']).read_bytes()
        assert core.sha((core.ROOT/d['source_path']).read_bytes())==d['source_sha256']
        assert (core.ROOT/d['source_path']).read_bytes()==(core.ROOT/d['preserved_source_path']).read_bytes()
    assert 'Say It Better' not in docs[2]['text']
    assert rules['captions']['required'] and rules['audio']['sfx'] is False and rules['visuals']['image_motion']=='static'

@pytest.mark.parametrize('fault',['missing','empty','truncated','wrong_hash','invalid_utf8','wrong_version'])
def test_skill_failures_block_actual_model_path(store,tmp_path,monkeypatch,fault):
    brand=tmp_path/'sources';shutil.copytree(core.ROOT/'brand',brand/'brand');shutil.copytree(core.ROOT/'prompts',brand/'prompts')
    target=brand/skills.PATHS[1]
    if fault=='missing':target.unlink()
    elif fault=='empty':target.write_bytes(b'')
    elif fault=='truncated':target.write_bytes(target.read_bytes()[:1000])
    elif fault=='wrong_hash':target.write_bytes(target.read_bytes()+b'changed')
    elif fault=='invalid_utf8':target.write_bytes(b'\xff')
    elif fault=='wrong_version':
        manifest=core.read_json(brand/'brand/SKILLS_MANIFEST.json');manifest['override_version']='bad';core.write_json(brand/'brand/SKILLS_MANIFEST.json',manifest)
    original=skills.model_request
    monkeypatch.setattr(creative,'model_request',lambda task,payload,config,**kwargs:original(task,payload,config,root=brand))
    called=[]
    monkeypatch.setattr(creative.httpx,'Client',lambda **kwargs:called.append(True))
    with pytest.raises((ValueError,OSError,UnicodeError)):
        creative.start_task('ideas',{})
    assert called==[]
    with core.db() as c:assert c.execute('SELECT count(*) FROM runs').fetchone()[0]==0

def test_context_bound_never_truncates():
    with pytest.raises(ValueError,match='Nothing was truncated'):
        skills.model_request('01_IDEA_GENERATION.md',{},dict(provider='manual',model='',context_tokens=1000,output_tokens=100))

def test_mock_model_receives_full_input_for_ideation_script_review_and_prepare(store,monkeypatch):
    # Inspect the actual API adapter request, not an isolated file existence check.
    monkeypatch.setenv('ODD_AI_PROVIDER','openai-compatible');monkeypatch.setenv('ODD_AI_MODEL','qa-mock');monkeypatch.setenv('ODD_AI_API_KEY','synthetic-test-only')
    inputs=[]
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,json,headers):
            inputs.append(json)
            task=json['messages'][0]['content']
            if '=== TASK ===\n# ODD FRAME — 01_IDEA' in task:
                result={'ideas':[{**IDEA,'title':f'QA concept {i}'} for i in range(10)]}
            elif '=== TASK ===\n# ODD FRAME — 04_CHARACTER' in task:result=package()
            else:result=SCRIPT
            return httpx.Response(200,json={'choices':[{'message':{'content':__import__('json').dumps(result)},'finish_reason':'stop'}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(creative.httpx,'Client',Client)
    ideas=creative.start_task('ideas',{})
    assert len(ideas['result']['ideas'])==10
    ep=creative.create_episode(ideas['result']['ideas'][0])
    creative.start_task('script',dict(idea=IDEA),ep['id'])
    assert core.episode(ep['id'])['status']=='AWAITING_APPROVAL'
    creative.approve(ep['id'],NARRATION)
    assert core.episode(ep['id'])['status']=='AWAITING_ASSETS'
    assert len(inputs)==4
    docs,rules=skills.load_skills()
    for request in inputs:
        system=request['messages'][0]['content']
        positions=[]
        for doc in docs:
            assert doc['text'] in system
            positions.append(system.index(doc['text']))
        assert positions==sorted(positions)
        assert system.rindex('CURRENT OVERRIDES: HIGHEST AUTHORITY')>positions[-1]
        assert 'prompts' not in request # no fake truncated document reference in place of content
        assert '"required": true' in system and '"sfx": false' in system
    evidence=core.read_json(creative.epdir(core.episode(ep['id']))/'reports/SKILL_PROVENANCE.json')
    assert len(evidence['runs'])==3 # episode script, review, preparation; ideation predates episode
    assert all(len(r['skills'])==4 and r['full_read_validated'] for r in evidence['runs'])

def test_provider_failure_is_not_success(store,monkeypatch):
    monkeypatch.setenv('ODD_AI_PROVIDER','openai-compatible');monkeypatch.delenv('ODD_AI_API_KEY',raising=False)
    with pytest.raises(ValueError,match='not configured'):creative.start_task('ideas',{})
    with core.db() as c:assert c.execute('SELECT status FROM runs').fetchone()[0]=='FAILED'

def test_approval_package_flow_isolation_and_idempotence(store):
    ep=prepared();directory=creative.epdir(ep)
    second=creative.create_episode({**IDEA,'title':'Second independent QA story'})
    assert ep['id']!=second['id'] and ep['path']!=second['path']
    assert not (creative.epdir(second)/'01_script/narration.txt').exists()
    flow=Flow.model_validate(core.read_json(directory/'04_google_flow/IMAGE_JOBS.json'))
    assert len(flow.jobs)==3 and all(j.type=='image' for j in flow.jobs)
    assert all('Mira' in j.prompt and 'ODD FRAME' in j.prompt and '#FFD43B' in j.prompt for j in flow.jobs)
    assert (directory/'01_script/narration.txt').read_text(encoding='utf-8')==NARRATION
    approval=creative.approved(ep);assert approval['auto_export'] and approval['sha256']==core.sha(NARRATION)
    assert creative.approve(ep['id'],NARRATION)['status']=='AWAITING_ASSETS'
    with pytest.raises(ValueError):creative.approve(ep['id'],NARRATION+' Changed.')
    with pytest.raises(ValueError):Flow.model_validate({**flow.model_dump(),'jobs':[{**flow.jobs[0].model_dump(),'type':'image_to_video'}]})
    report=media.validate_assets(ep['id'])
    assert not report['valid'] and any('S001' in s for s in report['errors'])
    assert 'FAILED' not in (directory/'production_status.json').read_text()

def test_invalid_package_cannot_complete(store):
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    run=creative.approve(ep['id'],NARRATION)
    bad=package();bad['scenes'][0]['narration_text']='A different story entirely.'
    with pytest.raises(ValueError,match='cover the approved narration'):creative.complete_run(run['run_id'],bad)
    assert core.episode(ep['id'])['status']=='AWAITING_MANUAL'
    assert not (creative.epdir(ep)/'04_google_flow/IMAGE_JOBS.json').exists()

def test_frozen_narration_detects_tampering(store):
    ep=prepared();core.textfile(creative.epdir(ep)/'01_script/narration.txt',NARRATION+' secret rewrite')
    with pytest.raises(ValueError,match='hash mismatch'):media.validate_assets(ep['id'])

def test_srt_and_timeline_do_not_invent_word_alignment(store,tmp_path):
    ep=prepared();path=tmp_path/'captions.srt'
    path.write_text('1\n00:00:00,000 --> 00:00:01,000\nThe key was gone.\n\n2\n00:00:01,000 --> 00:00:02,000\nThe door was open.\n\n3\n00:00:02,000 --> 00:00:03,000\nShe stayed outside.\n',encoding='utf-8')
    cues=media.parse_srt(path)
    report=dict(valid=True,cues=cues,sources={'narration':{'duration':3.1}},images={f'S{i:03d}':{'path':f'S{i:03d}.png'} for i in range(1,4)},fingerprints={})
    props=media.timeline(ep['id'],report)
    assert [s['start'] for s in props['scenes']]==[0,30,60]
    assert props['durationInFrames']==93 and len(props['captions'])==3
    assert all(s['motion']=='static' for s in props['scenes'])
    assert all(c['y']==.35 for c in props['captions']) # authored clue/face boxes protect the default center zone
    assert props['audioSources']==['narration','instrumental']
    path.write_text('1\n00:00:01,000 --> 00:00:00,000\nBad cue',encoding='utf-8')
    with pytest.raises(ValueError):media.parse_srt(path)

def test_caption_regions_and_queue_dedup(store):
    ep=prepared();s=package()['scenes'][0]
    s['protected_regions']=[dict(x=.1,y=.35,width=.8,height=.2)]
    assert media.caption_position(s)!=.46
    first=worker.enqueue(ep['id']);second=worker.enqueue(ep['id']);assert first==second

def test_skill_update_detected_on_manual_import(store,monkeypatch):
    run=creative.start_task('ideas',{})
    docs,rules=skills.load_skills();docs[0]={**docs[0],'sha256':'changed'}
    monkeypatch.setattr(creative,'load_skills',lambda *args:(docs,rules))
    with pytest.raises(ValueError,match='Skills changed'):creative.complete_run(run['run_id'],{'ideas':[IDEA]*10})

def test_http_api_import_and_path_safety(store,monkeypatch):
    monkeypatch.setattr(main,'start_worker',lambda:SimpleNamespace(join=lambda timeout:None))
    # API contract unit test: native MXC is exercised by the explicit isolation/media scripts.
    monkeypatch.setattr(main,'secure_validate',media.validate_assets)
    with TestClient(main.app) as client:
        client.headers['X-Odd-Controller']=core.controller_token()
        assert client.get('/api/status').json()['skills']['valid']
        assert client.post('/api/skills/validate').json()['valid']
        e=client.post('/api/episodes',json=IDEA).json();eid=e['id']
        assert client.post(f'/api/episodes/{eid}/draft',json=SCRIPT).status_code==200
        run=client.post(f'/api/episodes/{eid}/approve',json={'narration':NARRATION}).json()
        assert client.get('/api/runs/'+run['run_id']+'/request').status_code==200
        assert client.post('/api/runs/'+run['run_id']+'/import',json=package()).status_code==200
        assert client.get(f'/api/episodes/{eid}').json()['data']['approval']['auto_export']
        assert client.post(f'/api/episodes/{eid}/script').status_code==422
        refresh=client.post(f'/api/episodes/{eid}/assets/refresh')
        assert refresh.status_code==200 and not refresh.json()['valid']
        assert client.post(f'/api/episodes/{eid}/assets/images',files={'files':('wrong.png',b'junk','image/png')}).status_code==422
        assert client.get('/api/media/source_documents/OddFrame%20Design.md').status_code==404
        assert client.post('/api/skills/validate',headers={'Origin':'https://unrelated.example'}).status_code==403
        assert client.post(f'/api/episodes/{eid}/cancel-export').status_code==200
        assert client.post(f'/api/episodes/{eid}/retry').status_code==422

def asset_fixture(ep):
    import wave,math,struct
    from PIL import Image
    directory=creative.epdir(ep)
    for i in range(1,4):Image.new('RGB',(1080,1920),'#41464E').save(directory/f'05_assets/images/S{i:03d}.png')
    for kind in ['narration','music']:
        with wave.open(str(directory/f'05_assets/{kind}/test.wav'),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
            wav.writeframes(b''.join(struct.pack('<h',int(4000*math.sin(2*math.pi*200*i/16000))) for i in range(49600)))
    core.textfile(directory/'05_assets/subtitles/test.srt','1\n00:00:00,000 --> 00:00:01,000\nThe key was gone.\n\n2\n00:00:01,000 --> 00:00:02,000\nThe door was open.\n\n3\n00:00:02,000 --> 00:00:03,000\nShe stayed outside.\n')
    core.update_episode(ep['id'],music_rights={'instrumental_confirmed':True,'evidence':'Synthetic test tone'})
    return directory

@pytest.mark.parametrize('fault',['corrupt_image','text_mismatch','timing_outside_audio','extra_audio'])
def test_asset_validation_blocks_unusable_and_ungrounded_inputs(store,fault):
    from PIL import Image
    ep=prepared();directory=asset_fixture(ep)
    if fault=='corrupt_image':(directory/'05_assets/images/S001.png').write_bytes(b'not an image')
    srt=directory/'05_assets/subtitles/test.srt'
    if fault=='text_mismatch':core.textfile(srt,'1\n00:00:00,000 --> 00:00:01,000\nDifferent narration here.\n')
    if fault=='timing_outside_audio':core.textfile(srt,srt.read_text().replace('00:00:03,000','00:00:09,000'))
    if fault=='extra_audio':shutil.copyfile(directory/'05_assets/narration/test.wav',directory/'05_assets/narration/alternative.wav')
    report=media.validate_assets(ep['id'])
    assert not report['valid'] and report['errors']

def test_validation_cache_detects_replacement_even_with_same_timestamp(store):
    from PIL import Image
    import os
    ep=prepared();directory=asset_fixture(ep)
    report=media.validate_assets(ep['id']);assert report['valid']
    image=directory/'05_assets/images/S001.png';before=image.stat()
    image.write_bytes(b'x'*before.st_size)
    os.utime(image,ns=(before.st_atime_ns,before.st_mtime_ns))
    changed=media.validate_assets(ep['id'])
    assert not changed['valid']
    assert any(error.startswith('S001') for error in changed['errors'])

def test_resume_and_retry_queue_state(store,monkeypatch):
    ep=prepared();jid=worker.enqueue(ep['id'])
    with core.db() as c:c.execute("UPDATE jobs SET status='RUNNING' WHERE id=?",(jid,))
    class FakeThread:
        def __init__(self,**kwargs):pass
        def start(self):pass
    monkeypatch.setattr(worker.threading,'Thread',FakeThread)
    worker.start_worker()
    with core.db() as c:
        assert c.execute('SELECT status FROM jobs WHERE id=?',(jid,)).fetchone()[0]=='QUEUED'
        c.execute("UPDATE jobs SET status='FAILED' WHERE id=?",(jid,))
    assert worker.enqueue(ep['id'])!=jid

def test_post_approval_skill_change_blocks_preparation_retry(store,monkeypatch):
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    creative.approve(ep['id'],NARRATION)
    docs,rules=skills.load_skills();docs[0]={**docs[0],'sha256':'new reviewed skill version'}
    monkeypatch.setattr(creative,'load_skills',lambda *args:(docs,rules))
    with pytest.raises(ValueError,match='Skills changed after approval'):
        creative.start_task('prepare',dict(approved_narration=NARRATION),ep['id'])
    current=core.episode(ep['id'])
    assert current['status']=='BLOCKED' and current['data']['script']['narration']==NARRATION

def test_script_reapproval_has_new_version_not_false_old_evidence(store,monkeypatch):
    monkeypatch.setattr(main,'start_worker',lambda:SimpleNamespace(join=lambda timeout:None))
    with TestClient(main.app) as client:
        client.headers['X-Odd-Controller']=core.controller_token()
        ep=client.post('/api/episodes',json=IDEA).json();prefix=f'/api/episodes/{ep["id"]}'
        client.post(prefix+'/draft',json=SCRIPT)
        client.post(prefix+'/approve',json={'narration':NARRATION})
        assert client.post(prefix+'/revoke').status_code==200
        changed={**SCRIPT,'narration':NARRATION+' She never returned.'}
        client.post(prefix+'/draft',json=changed)
        assert client.post(prefix+'/approve',json={'narration':changed['narration']}).status_code==200
        current=client.get(prefix).json()
        assert current['data']['approval']['version']==2
        assert current['data']['approval']['sha256']!=core.sha(NARRATION)

def test_short_or_failed_model_response_is_not_accepted(store,monkeypatch):
    monkeypatch.setenv('ODD_AI_PROVIDER','openai-compatible');monkeypatch.setenv('ODD_AI_MODEL','mock');monkeypatch.setenv('ODD_AI_API_KEY','synthetic-test')
    class Truncated:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kwargs):return httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{"ideas":['}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(creative.httpx,'Client',Truncated)
    with pytest.raises(ValueError,match='AI request failed'):creative.start_task('ideas',{})
    with core.db() as c:
        run=c.execute('SELECT * FROM runs').fetchone()
        assert run['status']=='FAILED' and not run['result'] and 'incomplete' in run['error']

@pytest.mark.parametrize('mode',['partial','unreadable'])
def test_failed_full_read_cannot_be_reported_as_success(monkeypatch,mode):
    original=Path.read_bytes
    target=(core.ROOT/skills.PATHS[2]).resolve()
    def faulty_read(path):
        if path.resolve()==target and mode=='unreadable':
            raise PermissionError('Synthetic inaccessible skill file')
        raw=original(path)
        return raw[:1000] if path.resolve()==target else raw
    monkeypatch.setattr(Path,'read_bytes',faulty_read)
    state=skills.skill_status()
    assert not state['valid']
    assert next(d for d in state['documents'] if d['id']=='design')['status'] in ('FAILED','MISSING')

def test_caption_region_edit_changes_placement_without_rewriting_story(store,monkeypatch):
    ep=prepared()
    monkeypatch.setattr(main,'start_worker',lambda:SimpleNamespace(join=lambda timeout:None))
    with TestClient(main.app) as client:
        client.headers['X-Odd-Controller']=core.controller_token()
        rows=[dict(scene_id=s['scene_id'],caption_y=.35,protected_regions=[dict(x=.1,y=.6,width=.8,height=.2)]) for s in ep['data']['package']['scenes']]
        result=client.put(f'/api/episodes/{ep["id"]}/caption-regions',json=rows)
        assert result.status_code==200,result.text
        assert result.json()['data']['script']['narration']==NARRATION
        assert result.json()['data']['approval']['sha256']==core.sha(NARRATION)
        bad=copy.deepcopy(rows);bad[0]['beat']='Rewrite the story'
        assert client.put(f'/api/episodes/{ep["id"]}/caption-regions',json=bad).status_code==422


def test_owner_supplied_stills_are_not_aspect_ratio_policed(store):
    """The owner generated the artwork; only decodability matters (renderer uses contain, never stretches)."""
    from PIL import Image
    ep=prepared();directory=asset_fixture(ep)
    Image.new('RGB',(1920,1080),'#41464E').save(directory/'05_assets/images/S001.png')
    report=media.validate_assets(ep['id'])
    assert report['valid'],report['errors']

@pytest.mark.parametrize('fault',['cue_too_long','cross_scene_cue'])
def test_long_and_cross_scene_srt_cues_are_automatically_phrased(store,fault):
    ep=prepared();directory=asset_fixture(ep)
    srt=directory/'05_assets/subtitles/test.srt'
    if fault=='cue_too_long':core.textfile(srt,'1\n00:00:00,000 --> 00:00:03,000\n'+NARRATION+'\n')
    else:core.textfile(srt,'1\n00:00:00,000 --> 00:00:01,000\nThe key was\n\n2\n00:00:01,000 --> 00:00:02,000\ngone. The door was\n\n3\n00:00:02,000 --> 00:00:03,000\nopen. She stayed outside.\n')
    original=srt.read_bytes()
    report=media.validate_assets(ep['id'])
    assert report['valid'],report['errors']
    words=[len(creative.clean_words(c['text'])) for c in report['cues']]
    assert max(words)<=4
    assert creative.clean_words(' '.join(c['text'] for c in report['cues']))==creative.clean_words(NARRATION)
    assert all(a['end']<=b['start'] for a,b in zip(report['cues'],report['cues'][1:]))
    assert any('re-phrased' in w for w in report['warnings'])
    assert srt.read_bytes()==original  # the owner's file is never modified
