import copy,json,shutil,uuid
from pathlib import Path
import pytest
from pydantic import ValidationError
from services.api import core,creative,skills,snapshots,genres,story_ideas,main
from services.api.storytelling import load_extension,planning_context,validate_analysis,approved_context,validate_feedback,feedback_context
from services.api.storytelling_models import HumanMirror,RetentionAudit
from .fixtures import IDEA,SCRIPT,NARRATION,package
from .genre_fixtures import concept_batch
from .storytelling_fixtures import no_mirror,editorial_fields
from .storytelling_samples import DATA,script_sample,SECOND_COMEDY_BATCH

def config():return dict(provider='manual',model='',context_tokens=2000000,output_tokens=12000)
def old_source(tmp_path):
    target=tmp_path/'old-source';shutil.copytree(core.ROOT/'source_documents/storytelling/pre_v31',target)
    for entry in core.read_json(target/'brand/SKILLS_MANIFEST.json')['documents']:
        p=target/entry['canonical_path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(core.ROOT/entry['canonical_path'],p)
    for name in ['EDITING_PROFILES.json','STORY_GENRES.json']:shutil.copyfile(core.ROOT/'brand'/name,target/'brand'/name)
    return target

def test_complete_sources_extension_and_all_genres_remain_pinned(tmp_path):
    docs,_=skills.load_skills();assert len(docs)==4
    messages,evidence=skills.model_request('02_SCRIPT_WRITING.md',{},config())
    for d in docs:assert d['text'] in messages[0]['content']
    extension=load_extension(core.ROOT)
    assert extension['text'] in messages[0]['content']
    assert evidence['storytelling_extension']['version']=='3.1.0'
    ep=tmp_path/'snapshot';ep.mkdir();snapshots.bootstrap(ep)
    text=(ep/'.production/input_snapshot/brand/storytelling/ODD_FRAME_STORYTELLING_V3_1.md')
    assert text.read_text(encoding='utf-8')==extension['text']
    text.write_text('truncated',encoding='utf-8')
    with pytest.raises(ValueError,match='Pinned episode input'):snapshots.validate(ep)
    taxonomy=genres.load();assert len(taxonomy['groups'])==8 and sum(len(g['genres']) for g in taxonomy['groups'])==24

def test_legacy_snapshot_has_no_new_required_analysis(tmp_path):
    old=old_source(tmp_path);assert load_extension(old) is None
    raw={k:v for k,v in SCRIPT.items() if k not in ('human_mirror','retention_audit')}
    validate_analysis(old,'script',raw,{})
    messages,evidence=skills.model_request('02_SCRIPT_WRITING.md',{},config(),root=old)
    assert evidence['master_prompt']['version']=='2.0.0' and 'storytelling_extension' not in evidence
    assert '45–75' in messages[0]['content']
    ep=tmp_path/'historical';ep.mkdir();snapshots.bootstrap(ep,source_root=old)
    assert snapshots.source_root(ep).joinpath('prompts/00_MASTER_PROMPT.md').read_bytes()==(old/'prompts/00_MASTER_PROMPT.md').read_bytes()

def test_missing_or_modified_extension_fails_closed(tmp_path):
    root=tmp_path/'copy';shutil.copytree(core.ROOT/'brand',root/'brand');shutil.copytree(core.ROOT/'prompts',root/'prompts')
    (root/'brand/storytelling/POLICY_V3_1.json').write_text('{}')
    with pytest.raises(ValueError,match='extension changed'):skills.load_skills(root)
    manifest=core.read_json(root/'brand/SKILLS_MANIFEST.json');manifest.pop('storytelling_extension');core.write_json(root/'brand/SKILLS_MANIFEST.json',manifest)
    with pytest.raises(ValueError,match='requires its registered'):skills.load_skills(root)

def test_none_is_fully_valid_and_fake_parallel_rejected():
    assert HumanMirror.model_validate(no_mirror()).mode=='none'
    for patch in [dict(has_meaningful_parallel=True),dict(human_behavior='Greed'),dict(reflective_ending_recommended=True),dict(real_world_connection='Invented link')]:
        with pytest.raises(ValidationError):HumanMirror.model_validate({**no_mirror(),**patch})
    with pytest.raises(ValidationError):HumanMirror.model_validate({**no_mirror(), 'mode':'natural'})

def test_new_analysis_requires_complete_logic_not_duplicate_checks():
    data=copy.deepcopy(SCRIPT);data['retention_audit']['logic_checks'][1]=data['retention_audit']['logic_checks'][0]
    with pytest.raises(ValidationError,match='ten distinct'):RetentionAudit.model_validate(data['retention_audit'])
    with pytest.raises(ValueError,match='Human Mirror'):validate_analysis(core.ROOT,'script',{'narration':NARRATION},{})
    validate_analysis(core.ROOT,'script',SCRIPT,{'genre_context':{'human_mirror_preference':'pure_entertainment'}})
    data=copy.deepcopy(SCRIPT);data['human_mirror'].update(mode='natural',has_meaningful_parallel=True,human_behavior='Insecurity',real_world_connection='A specific recognizable decision.')
    with pytest.raises(ValueError,match='Pure entertainment preference'):validate_analysis(core.ROOT,'script',data,{'genre_context':{'human_mirror_preference':'pure_entertainment'}})

def test_duration_without_calibration_never_invents_speech_rate():
    timing=planning_context(core.ROOT,{})['timing']
    assert timing['preferred_seconds']==[40,55] and not timing['strict_limit']
    assert timing['word_budget'] is None and timing['measured_voice_wpm'] is None
    timing=planning_context(core.ROOT,dict(voice_calibration=dict(voice='Measured QA voice',measured_words=120,measured_seconds=60,source='Explicit measured test fixture, not a real ElevenLabs claim',observed_at='2026-11-06')))['timing']
    assert timing['measured_voice_wpm']==120 and timing['word_budget']==[80,110]

def test_preference_persists_and_new_batch_validation_precedes_save(store):
    s=story_ideas.create_session(dict(category_group_id='comedy_dark_comedy',primary_genre_id='comedy',human_mirror_preference='pure_entertainment'))
    assert story_ideas.session_details(s['id'])['selection']['human_mirror_preference']=='pure_entertainment'
    batch=story_ideas.start_batch(s['id'],dict(idempotency_key=uuid.uuid4().hex))
    with core.db() as c:run=dict(c.execute('SELECT * FROM runs WHERE id=?',(batch['run_id'],)).fetchone())
    payload=json.loads(json.loads(run['request'])['messages'][1]['content']);result=concept_batch(payload)
    bad=copy.deepcopy(result);bad['ideas'][0].pop('human_mirror')
    with pytest.raises(ValueError,match='Human Mirror'):creative.complete_run(run['id'],bad,manual=True)
    assert not (Path(run['workspace'])/'batches'/f"{batch['batch_id']}.json").exists()
    creative.complete_run(run['id'],result,manual=True)
    assert len(story_ideas.session_details(s['id'])['batches'][0]['result']['ideas'])==5

def test_review_hash_freshness_single_approval_and_metadata(store):
    ep=creative.create_episode(IDEA);run=creative.start_task('script',dict(idea=IDEA),ep['id'])
    review=creative.complete_run(run['run_id'],SCRIPT,manual=True)
    creative.complete_run(review['run_id'],SCRIPT,manual=True)
    draft=core.episode(ep['id'])['data']['script']
    assert approved_context(draft,NARRATION)['review_matches_approved_wording']
    changed=NARRATION+' She waited.'
    main.draft(ep['id'],dict(narration=changed,brief=SCRIPT['brief'],findings=['Explicit owner edit.']))
    draft=core.episode(ep['id'])['data']['script']
    assert not approved_context(draft,changed)['review_matches_approved_wording']
    prepare=creative.approve(ep['id'],changed)
    assert not core.episode(ep['id'])['data']['approval']['storytelling_context']['review_matches_approved_wording']
    with pytest.raises(ValueError,match='locked'):main.draft(ep['id'],dict(narration=NARRATION,brief=SCRIPT['brief'],findings=['Must not write.']))
    assert core.episode(ep['id'])['data']['script']['narration']==changed

def test_feedback_is_sparse_observational_and_not_derived(store):
    ep=creative.create_episode(IDEA)
    payload=dict(period='Early snapshot',source='Owner fixture',observed_at='2026-11-06',source_definitions='Views include replays; viewers reported separately',runtime_seconds=107,views=133,viewers=12,average_watch_seconds=12,retention_observations='Synthetic QA observation, not an actual Meta import')
    main.save_metrics(ep['id'],payload)
    feedback=feedback_context();assert feedback['observations'][0]['views']==133 and feedback['observations'][0]['viewers']==12
    assert 'completion_rate' not in feedback['observations'][0] and 'No causal claim' in feedback['interpretation']
    with pytest.raises(ValueError,match='observed_at'):validate_feedback(dict(runtime_seconds=50))
    with pytest.raises(ValueError,match='finite'):validate_feedback(dict(views=float('nan')))

def test_approved_editorial_context_reaches_timeline_and_official_studio(store,monkeypatch):
    from services.api import media,studio
    from .test_editor_activity import make_draft
    ep,root=make_draft(store,monkeypatch)
    context=approved_context(SCRIPT,NARRATION)
    approval=core.episode(ep['id'])['data']['approval']
    approval['storytelling_context']=context
    core.update_episode(ep['id'],approval=approval)
    report=media.validate_assets(ep['id']);assert report['valid']
    props=media.timeline(ep['id'],report)
    assert props['storytelling_metadata']==context
    assert props['audioSources']==['narration','instrumental'] and len(props['scenes'])==3
    monkeypatch.setattr(studio,'STORE',store)
    # Use real prepared audio/envelope, rather than constructing a fake Studio payload.
    prepared_props=core.read_json(root/'06_edit/revisions/000001.json')
    prepared_props['storytelling_metadata']=props['storytelling_metadata']
    manifest=studio.generate(root,prepared_props,ep['data']['package']['scenes'],ep['code'],force=True)
    assert manifest['storytelling_metadata']==context
    assert studio.check_source(root)['errors']==[]

@pytest.mark.parametrize('case',DATA['genre_cases'],ids=lambda row:row[0])
def test_all_24_genre_requests_keep_identity_and_optional_mirror(case):
    genre_id,title,premise,mode,editorial=case
    taxonomy=genres.load();group=next(g for g in taxonomy['groups'] if any(x['id']==genre_id for x in g['genres']))
    payload=dict(genre_context=dict(category_group_id=group['id'],primary_genre_id=genre_id,human_mirror_preference='automatic'),premise=premise)
    messages,evidence=skills.model_request('02_SCRIPT_WRITING.md',payload,config())
    assert json.loads(messages[1]['content'])['genre_context']['primary_genre_id']==genre_id
    assert 'never genre alone' in messages[0]['content'] and 'Pure entertainment is fully successful' in messages[0]['content']
    assert evidence['full_read_validated'] and mode in ('natural','subtle','none') and len(editorial)>40

@pytest.mark.parametrize('index',range(6),ids=[x['genre'] for x in DATA['scripts']])
def test_six_authored_script_samples_are_structurally_valid_not_quality_proof(index):
    from services.api.models import Script
    data=Script.model_validate(script_sample(index)).model_dump()
    validate_analysis(core.ROOT,'script',data,{})
    assert data['narration']==DATA['scripts'][index]['narration']
    assert 'moral of the story' not in data['narration'].lower()
    assert data['retention_audit']['duration_note'].startswith('40–55 seconds is the soft')

def test_two_distinct_batches_preserve_none_and_meaningful_connections(store,monkeypatch):
    from . import genre_fixtures
    s=story_ideas.create_session(dict(category_group_id='comedy_dark_comedy',primary_genre_id='comedy'))
    old_contents=[]
    for i in range(2):
        batch=story_ideas.start_batch(s['id'],dict(idempotency_key=uuid.uuid4().hex))
        with core.db() as c:run=dict(c.execute('SELECT * FROM runs WHERE id=?',(batch['run_id'],)).fetchone())
        payload=json.loads(json.loads(run['request'])['messages'][1]['content'])
        if i:monkeypatch.setattr(genre_fixtures,'CASES',SECOND_COMEDY_BATCH)
        result=concept_batch(payload)
        if i:result['ideas'][0]['human_mirror']=script_sample(1)['human_mirror']
        creative.complete_run(run['id'],result,manual=True)
        path=Path(run['workspace'])/'batches'/f"{batch['batch_id']}.json"
        old_contents.append((path,path.read_bytes()))
    state=story_ideas.session_details(s['id']);assert len(state['batches'])==2
    assert len({idea['title'] for b in state['batches'] for idea in b['result']['ideas']})==10
    assert {idea['human_mirror']['mode'] for b in state['batches'] for idea in b['result']['ideas']}=={'none','subtle'}
    assert all(path.read_bytes()==raw for path,raw in old_contents)
