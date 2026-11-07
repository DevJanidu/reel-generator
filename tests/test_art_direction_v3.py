"""No provider usage. Approval exists ONLY in disposable test sources."""
import copy
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api import core,skills,snapshots,continuity,creative,main
from services.api.models import Flow
from scripts.approve_art_direction import approve
from .fixtures import package,NARRATION,IDEA,SCRIPT

CONFIG=dict(provider='manual',model='',output_tokens=12000,context_tokens=200000)


@pytest.fixture
def approved_source(tmp_path):
    source=tmp_path/'synthetic-approved-source'
    shutil.copytree(core.ROOT/'brand',source/'brand')
    shutil.copytree(core.ROOT/'prompts',source/'prompts')
    approve(source,approved_by='Synthetic acceptance fixture; NOT global owner approval')
    return source


def test_candidate_is_complete_valid_and_not_silently_approved(tmp_path):
    source=tmp_path/'pending-source';shutil.copytree(core.ROOT/'brand',source/'brand')
    manifest=core.read_json(source/'brand/SKILLS_MANIFEST.json')
    manifest['visual_art_direction'].update(approved=None,required=False)
    core.write_json(source/'brand/SKILLS_MANIFEST.json',manifest)
    assert manifest['visual_art_direction']['approved'] is None
    loaded=skills.validate_art_direction(manifest['visual_art_direction']['candidate'],source)
    assert len(loaded['text'].encode())==loaded['byte_length']
    assert loaded['version']=='3.0.0' and loaded['status']=='ready-for-owner-approval'
    assert skills.load_art_direction(source) is None
    assert len(skills.load_skills(source)[0])==4
    with pytest.raises(ValueError,match='not approved'):skills.load_art_direction(source,required=True)


def test_complete_skill_is_delivered_and_context_budget_is_honest(approved_source):
    loaded=skills.load_art_direction(approved_source)
    messages,evidence=skills.model_request('04_CHARACTER_BIBLE.md',dict(approved_narration=NARRATION),CONFIG,root=approved_source)
    assert loaded['text'] in messages[0]['content']
    for doc in skills.load_skills(approved_source)[0]:assert doc['text'] in messages[0]['content']
    receipt=evidence['visual_art_direction']
    assert receipt['version']=='3.0.0' and receipt['canonical_path']==skills.ART_PATH
    assert receipt['sha256']==core.sha((approved_source/skills.ART_PATH).read_bytes())
    assert receipt['loaded_at'] and receipt['full_read_validated']
    with pytest.raises(ValueError,match='Nothing was truncated'):
        skills.model_request('04_CHARACTER_BIBLE.md',{},dict(CONFIG,context_tokens=1000),root=approved_source)


@pytest.mark.parametrize('fault',['missing','empty','truncated','wrong-version','disabled','profile','unreadable'])
def test_bad_skill_blocks_before_any_model_request(approved_source,monkeypatch,fault):
    path=approved_source/skills.ART_PATH
    manifest=core.read_json(approved_source/'brand/SKILLS_MANIFEST.json')
    if fault=='missing':path.unlink()
    elif fault=='empty':path.write_bytes(b'')
    elif fault=='truncated':path.write_bytes(path.read_bytes()[:400])
    elif fault=='wrong-version':
        manifest['visual_art_direction']['approved']['version']='2.0.0'
        core.write_json(approved_source/'brand/SKILLS_MANIFEST.json',manifest)
    elif fault=='disabled':
        manifest['visual_art_direction']['approved']=None
        core.write_json(approved_source/'brand/SKILLS_MANIFEST.json',manifest)
    elif fault=='profile':(approved_source/skills.ART_PROFILE_PATH).write_bytes(b'{}')
    elif fault=='unreadable':
        original=Path.read_bytes
        def fail(self):
            if self==path:raise PermissionError('Synthetic unreadable skill')
            return original(self)
        monkeypatch.setattr(Path,'read_bytes',fail)
    with pytest.raises(ValueError):skills.model_request('04_CHARACTER_BIBLE.md',{},CONFIG,root=approved_source)


def test_episode_pins_the_entire_approved_skill_and_profile(approved_source,tmp_path):
    root=tmp_path/'pinned-episode';root.mkdir()
    record=snapshots.bootstrap(root,source_root=approved_source)
    assert record['visual_art_direction']['version']=='3.0.0'
    pinned=snapshots.source_root(root)
    assert (pinned/skills.ART_PATH).read_bytes()==(approved_source/skills.ART_PATH).read_bytes()
    assert (pinned/skills.ART_PROFILE_PATH).read_bytes()==(approved_source/skills.ART_PROFILE_PATH).read_bytes()
    (approved_source/skills.ART_PATH).write_bytes(b'Global changes cannot repin an existing episode')
    loaded=skills.episode_art_direction(root)
    assert loaded['version']=='3.0.0' and 'READ BEFORE WRITING' in loaded['text']
    (pinned/skills.ART_PATH).write_bytes(b'tampered snapshot')
    with pytest.raises(ValueError,match='Pinned episode input was changed'):continuity.compile_plan(package(),NARRATION,'OF_QA',root)
    (root/'.production/provenance.json').unlink()
    with pytest.raises(ValueError,match='cannot fall back'):continuity.compile_plan(package(),NARRATION,'OF_QA',root)


def test_historical_snapshot_retains_legacy_style(approved_source,tmp_path):
    historical=tmp_path/'historical-source'
    shutil.copytree(core.ROOT/'brand',historical/'brand');shutil.copytree(core.ROOT/'prompts',historical/'prompts')
    manifest=core.read_json(historical/'brand/SKILLS_MANIFEST.json');manifest.pop('visual_art_direction')
    core.write_json(historical/'brand/SKILLS_MANIFEST.json',manifest)
    root=tmp_path/'historical-episode';root.mkdir();snapshots.bootstrap(root,source_root=historical)
    before=continuity.compile_plan(package(),NARRATION,'OF_OLD',root)
    assert before['generation_manifest'] is None
    assert continuity.STYLE in before['flow']['jobs'][0]['prompt']
    assert skills.load_art_direction(approved_source)['version']=='3.0.0'
    after=continuity.compile_plan(package(),NARRATION,'OF_OLD',root)
    assert after['flow']==before['flow']


def test_initial_prepare_and_regeneration_read_full_pinned_skill(store,approved_source,monkeypatch):
    # Explicit test-only capacity. Never raise the owner's real provider limits.
    with core.db() as c:c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)',('context_tokens','250000'))
    bootstrap=snapshots.bootstrap
    monkeypatch.setattr(snapshots,'bootstrap',lambda root:bootstrap(root,source_root=approved_source))
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    run=creative.approve(ep['id'],NARRATION)
    root=creative.epdir(core.episode(ep['id']))
    request=core.read_json(root/f'.production/runs/{run["run_id"]}/request.json')
    assert (approved_source/skills.ART_PATH).read_text(encoding='utf-8') in request['request']['messages'][0]['content']
    reads=[];read_bytes=Path.read_bytes
    def observed(path):
        if path==root/'.production/input_snapshot'/skills.ART_PATH:reads.append(path)
        return read_bytes(path)
    monkeypatch.setattr(Path,'read_bytes',observed)
    creative.complete_run(run['run_id'],package(),manual=True)
    before=len(reads);assert before>0
    manifest=core.read_json(root/'04_google_flow/GENERATION_MANIFEST.json')
    assert manifest['skill']['version']=='3.0.0' and manifest['skill']['full_read_validated']
    assert manifest['visual_bible_version']=='1.0.0'
    assert manifest['visual_validation']=='NOT_PERFORMED'
    assert manifest['queue_readiness']=='PROMPT_VALIDATED'
    original=core.read_json(root/'04_google_flow/IMAGE_JOBS.json')
    client=TestClient(main.app)
    result=client.post(f'/api/episodes/{ep["id"]}/continuity/regenerate/S001',headers={'X-Odd-Controller':core.controller_token()})
    assert result.status_code==200,result.text
    assert len(reads)>before
    regenerated=core.read_json(root/result.json()['path'])
    assert regenerated['jobs'][0]['prompt']==original['jobs'][0]['prompt']
    sidecar=core.read_json(root/result.json()['path'].replace('.json','.manifest.json'))
    assert sidecar['generation']['skill']['version']=='3.0.0'
    assert sidecar['generation']['skill']['loaded_at']!=manifest['skill']['loaded_at']
    # A pinned v3 skill cannot disappear and fall back on the second regeneration.
    (root/'.production/input_snapshot'/skills.ART_PATH).unlink()
    failed=client.post(f'/api/episodes/{ep["id"]}/continuity/regenerate/S001',headers={'X-Odd-Controller':core.controller_token()})
    assert failed.status_code==422


def test_schema_compaction_preserves_real_title_fields_and_constraints():
    schema=dict(type='object',title='Display name',properties={'title':dict(type='string',title='Display label',minLength=4)},required=['title'])
    compact=skills.compact_schema_annotations(schema)
    assert compact==dict(type='object',properties={'title':dict(type='string',minLength=4)},required=['title'])
    assert schema['title']=='Display name'  # no mutation of the original schema


def test_background_cli_boundary_and_explicit_retry_receive_full_skill(store,approved_source,monkeypatch):
    import time
    bootstrap=snapshots.bootstrap
    monkeypatch.setattr(snapshots,'bootstrap',lambda root:bootstrap(root,source_root=approved_source))
    with core.db() as c:
        for key,value in [('provider','codex_cli'),('context_tokens',250000)]:
            c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)',(key,json.dumps(value)))
    full=(approved_source/skills.ART_PATH).read_text(encoding='utf-8');calls=[]
    def mock_cli(config,messages,schema,root,runid,cancel=None):
        assert config['provider']=='codex_cli' and full in messages[0]['content']
        calls.append(runid)
        if len(calls)==1:raise creative.providers.ProviderError('Synthetic test timeout','TIMEOUT')
        return package()
    monkeypatch.setattr(creative.providers,'generate',mock_cli)
    def terminal(runid):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            with core.db() as c:row=dict(c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone())
            if row['status'] in ('FAILED','SUCCEEDED','CANCELLED') and runid not in creative._cancellations:return row
            time.sleep(.05)
        raise AssertionError('Synthetic background job did not finish')
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    initial=creative.approve(ep['id'],NARRATION,background=True)
    first=terminal(initial['run_id']);assert first['status']=='FAILED'
    retry=main.retry_generation(initial['run_id'])
    second=terminal(retry['run_id']);assert second['status']=='SUCCEEDED',second['error']
    assert len(calls)==2
    evidence=json.loads(second['provenance'])
    assert evidence['attempt_number']==2 and evidence['retry_of']==initial['run_id']
    assert evidence['visual_art_direction']['full_read_validated']
    assert evidence['visual_art_direction']['version']=='3.0.0'
    assert json.loads(first['provenance'])['visual_art_direction']['sha256']==evidence['visual_art_direction']['sha256']


def test_episode_process_cannot_activate_the_global_skill(approved_source,monkeypatch):
    path=approved_source/'brand/SKILLS_MANIFEST.json';before=path.read_bytes()
    monkeypatch.setenv('ODD_EXECUTION_MODE','episode')
    with pytest.raises(ValueError,match='cannot approve'):approve(approved_source)
    assert path.read_bytes()==before


def test_essential_missing_reference_never_yields_v3_ready(approved_source,tmp_path):
    root=tmp_path/'blocked-episode';root.mkdir();snapshots.bootstrap(root,source_root=approved_source)
    p=package();bible=p['visual_continuity']['bible']
    bible['assets'][0]['reference_ids']=['REF_ESSENTIAL']
    bible['references']=[dict(id='REF_ESSENTIAL',category='character',path=None,sha256=None,approved=False,essential=True)]
    result=continuity.compile_plan(p,NARRATION,'OF_QA',root)
    assert result['flow'] is None
    assert result['generation_manifest']['queue_readiness']=='BLOCKED'
    assert result['generation_manifest']['skill']['full_read_validated']


@pytest.mark.parametrize('field,text',[('composition','A split-screen comic panel layout with both moments.'),('profile','A technical elevation in an engineering survey drawing.')])
def test_final_qa_also_checks_panels_and_profile_language(approved_source,tmp_path,field,text):
    if field=='profile':
        profile=approved_source/skills.ART_PROFILE_PATH
        data=core.read_json(profile);data['style']=text;core.write_json(profile,data)
        manifest=core.read_json(approved_source/'brand/SKILLS_MANIFEST.json')
        manifest['visual_art_direction']['approved'].update(profile_sha256=core.sha(profile.read_bytes()),profile_byte_length=len(profile.read_bytes()))
        core.write_json(approved_source/'brand/SKILLS_MANIFEST.json',manifest)
    root=tmp_path/'bad-shot';root.mkdir();snapshots.bootstrap(root,source_root=approved_source)
    p=package()
    if field=='composition':p['visual_continuity']['ledger']['shots'][0]['composition']=text
    result=continuity.compile_plan(p,NARRATION,'OF_QA',root)
    assert result['flow'] is None and result['report']['status']=='BLOCKED'


@pytest.mark.parametrize('genre,species,prop,beats',[
    ('Mystery','rabbit','key',['A rabbit discovers an empty key hook.','The rabbit finds the missing key beneath a leaf.','The rabbit returns the key to the hook.']),
    ('Comedy','otter','bag',['The animals exchange bags.','They discover their mistake.','They return the bags.']),
    ('Friendship','raccoon','scarf',['A raccoon finds a lost scarf beside a bench.','The raccoon folds the scarf carefully for a friend.','The raccoon leaves the scarf on the bench for the returning friend.']),
    ('OF_R002','beaver','stake',[]),
])
def test_v3_examples_with_distinct_lighting_and_locked_materials(approved_source,tmp_path,monkeypatch,genre,species,prop,beats):
    from . import test_continuity as fixtures
    from scripts.continuity_regression import river_plan
    root=tmp_path/'example-episode';root.mkdir();snapshots.bootstrap(root,source_root=approved_source)
    captured=[]
    def capture(p=None,root_argument=None,narration=NARRATION):
        p=copy.deepcopy(p or package())
        if genre=='Mystery':
            p['visual_continuity']['bible']['palette_lighting']='Soft natural moonlight with readable facial features and restrained reflected highlights.'
            for shot in p['visual_continuity']['ledger']['shots']:shot['lighting']='Soft moonlight from the left, with gentle illustrated shadows to the right.'
        elif genre=='Friendship':
            p['visual_continuity']['bible']['palette_lighting']='Warm afternoon sunlight illuminates the established weathered wooden bench and wooden boardwalk.'
            for shot in p['visual_continuity']['ledger']['shots']:
                shot['lighting']='Warm afternoon sunlight from the left, gentle natural shadows to the right.'
                shot['geography']='A weathered wooden boardwalk runs beside a garden bench; preserve the timber floor.'
        result=continuity.compile_plan(p,narration,'OF_SYNTHETIC_V3',root);captured.append(result)
        return result
    if genre=='OF_R002':
        original=core.ROOT/'episodes/OF_R002_the-stakes-in-the-river/episode.json'
        raw=original.read_bytes();source=json.loads(raw)
        result=capture(river_plan(source),narration=source['data']['script']['narration'])
        assert original.read_bytes()==raw
        assert result['report']['status']=='REVIEW'
        assert 'Neutral overcast skylight' in result['flow']['jobs'][0]['prompt']
    else:
        monkeypatch.setattr(fixtures,'compile',capture)
        fixtures.test_six_genres_without_river_contamination(genre,species,prop,beats,tmp_path)
    result=next(r for r in captured if r['flow'])
    flow=Flow.model_validate(result['flow'])
    profile=skills.load_art_direction(approved_source)['profile']
    for job in flow.jobs:
        assert job.prompt.startswith(profile['opening'])
        assert 'dominate environmental materials' not in job.prompt
        assert 'warm sandy dirt' not in job.prompt and 'dry-earth plates' not in job.prompt
        assert job.source_image is None
        assert not continuity.lint(job.prompt.split(profile['style'])[0])
    text=' '.join(j.prompt for j in flow.jobs)
    if genre=='Mystery':assert 'moonlight' in text
    if genre=='Friendship':assert 'wooden boardwalk' in text and 'Warm afternoon sunlight' in text
    if genre=='Comedy':assert 'afternoon daylight' in text
    core.write_json(root/'IMAGE_JOBS.json',flow.model_dump())
    core.write_json(root/'REFERENCE_MANIFEST.json',result['references'])
    core.write_json(root/'GENERATION_MANIFEST.json',result['generation_manifest'])
    core.write_json(root/'TEST_ONLY.json',dict(not_production_approval=True,genre=genre,visual_inspection='NOT_PERFORMED'))
