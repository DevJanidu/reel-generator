import copy,json,uuid
import pytest
from services.api import core,creative,genres,story_ideas,providers,snapshots
from .genre_fixtures import concept_batch

def session():return story_ideas.create_session(dict(category_group_id='comedy_dark_comedy',primary_genre_id='comedy'))
def queued(s):
    batch=story_ideas.start_batch(s['id'],dict(idempotency_key=uuid.uuid4().hex))
    with core.db() as c:run=dict(c.execute('SELECT * FROM runs WHERE id=?',(batch['run_id'],)).fetchone())
    payload=json.loads(json.loads(run['request'])['messages'][1]['content'])
    return batch,run,payload

def test_taxonomy_has_all_24_unique_genres_in_eight_groups():
    doc=genres.load();assert len(doc['groups'])==8
    items=[g for group in doc['groups'] for g in group['genres']]
    assert len(items)==len({g['id'] for g in items})==24
    assert {g['id'] for g in items}==set('mystery suspense crime_detective unexplained_surreal comedy dark_comedy dark_irony betrayal revenge jealousy_rivalry emotional_drama friendship family_drama heartbreak wholesome_heartwarming horror psychological_thriller fantasy adventure science_fiction survival cleverness_strategy plot_twists romance'.split())
    assert doc['groups'][-1]['name']=='ROMANCE & OTHER'

def test_bad_genre_pair_is_rejected_and_surprise_stays_in_group(store):
    with pytest.raises(ValueError):story_ideas.create_session(dict(category_group_id='romance_other',primary_genre_id='horror'))
    selected=story_ideas.create_session(dict(category_group_id='romance_other',surprise=True))
    assert selected['selection']['primary_genre_id']=='romance'
    assert selected['selection']['surprise']

def test_dashboard_default_story_preferences_are_accepted_and_persisted(store):
    created=story_ideas.create_session(dict(category_group_id='comedy_dark_comedy',primary_genre_id='comedy',
                                          human_mirror_preference='automatic',voice_calibration=None))
    restored=story_ideas.session_details(created['id'])
    assert restored['selection']['human_mirror_preference']=='automatic'
    assert restored['selection']['voice_calibration'] is None

def test_full_pinned_request_includes_actual_selection_and_schema(store):
    s=session();batch,run,payload=queued(s)
    assert payload['idea_count']==5 and payload['primary_genre_id']=='comedy'
    assert payload['output_json_schema']['properties']['ideas']['minItems']==5
    assert payload['output_json_schema']['$defs']['StoryConcept']['properties']['primary_genre_id']['const']=='comedy'
    request=json.loads(run['request']);docs,_=creative.load_skills(snapshots.source_root(story_ideas._root(s['id'])))
    assert all(d['text'] in request['messages'][0]['content'] for d in docs)
    assert 'COMPLETE PINNED STORY GENRE TAXONOMY' in request['messages'][0]['content']
    assert run['status']=='AWAITING_MANUAL'

def test_manual_validates_exactly_five_and_persists_batch_metadata(store):
    s=session();batch,run,payload=queued(s);valid=concept_batch(payload)
    creative.complete_run(run['id'],valid,manual=True)
    restored=story_ideas.session_details(s['id']);b=restored['batches'][0]
    assert b['status']=='SUCCEEDED' and len(b['result']['ideas'])==5
    assert b['result']['master_prompt']['version']=='3.1.0'
    assert len(b['result']['skill_versions'])==4 and b['result']['taxonomy']['version']=='2.0.0'
    assert story_ideas.list_sessions()[0]['id']==s['id']

@pytest.mark.parametrize('fault',['short','wrong_genre','extra_field','duplicate_id','near_duplicate','incomplete_audit'])
def test_invalid_concept_batches_are_never_saved(store,fault):
    s=session();batch,run,payload=queued(s);data=concept_batch(payload)
    if fault=='short':data['ideas'].pop()
    if fault=='wrong_genre':data['ideas'][1]['primary_genre_id']='horror'
    if fault=='extra_field':data['ideas'][0]['shell_command']='anything'
    if fault=='duplicate_id':data['ideas'][1]['idea_id']=data['ideas'][0]['idea_id']
    if fault=='near_duplicate':
        data['ideas'][1]={**data['ideas'][0],'idea_id':data['ideas'][1]['idea_id'],'title':'Different title, same underlying plot'}
    if fault=='incomplete_audit':data['ideas'][0]['quality_audit'].pop()
    with pytest.raises(ValueError):creative.complete_run(run['id'],data,manual=True)
    saved=story_ideas.session_details(s['id'])['batches'][0]
    assert 'result' not in saved and saved['validation_error']

def test_duplicate_submission_is_idempotent_and_prior_batches_are_preserved(store):
    s=session();key=uuid.uuid4().hex
    first=story_ideas.start_batch(s['id'],dict(idempotency_key=key))
    again=story_ideas.start_batch(s['id'],dict(idempotency_key=key));assert first['run_id']==again['run_id']
    with core.db() as c:run=dict(c.execute('SELECT * FROM runs WHERE id=?',(first['run_id'],)).fetchone())
    payload=json.loads(json.loads(run['request'])['messages'][1]['content']);creative.complete_run(run['id'],concept_batch(payload),manual=True)
    original=story_ideas.session_details(s['id'])['batches'][0]['result']
    second,run2,payload2=queued(s)
    assert len(payload2['prior_concepts'])==5
    with pytest.raises(ValueError,match='previous session batch'):creative.complete_run(run2['id'],concept_batch(payload2,rotation=1),manual=True)
    assert story_ideas.session_details(s['id'])['batches'][0]['result']==original

def test_selecting_a_concept_keeps_genre_and_starts_existing_manual_script_stage(store):
    s=session();batch,run,payload=queued(s);data=concept_batch(payload);creative.complete_run(run['id'],data,manual=True)
    chosen=story_ideas.select_story(s['id'],batch['batch_id'],data['ideas'][0]['idea_id'])
    ep=core.episode(chosen['episode_id']);assert ep['data']['genre_selection']['primary_genre_id']=='comedy'
    assert ep['data']['genre_selection']['idea_batch_id']==batch['batch_id']
    assert ep['data']['genre_selection']['master_prompt']['version']=='3.1.0'
    with core.db() as c:script=dict(c.execute('SELECT * FROM runs WHERE id=?',(chosen['run_id'],)).fetchone())
    body=json.loads(json.loads(script['request'])['messages'][1]['content'])
    assert body['genre_context']['primary_genre_id']=='comedy' and body['selected_story_concept']['title']==data['ideas'][0]['title']
    assert script['status']=='AWAITING_MANUAL'
    assert story_ideas.select_story(s['id'],batch['batch_id'],data['ideas'][0]['idea_id'])['episode_id']==ep['id']

def test_custom_premise_conflict_needs_explicit_choice_and_input_is_retained(store):
    s=story_ideas.create_session(dict(category_group_id='romance_other',primary_genre_id='romance'))
    original=dict(idempotency_key=uuid.uuid4().hex,title='The Haunted Hotel',premise='A terrifying monster guards a haunted hotel. There is no love.')
    assert story_ideas.check_custom(s['id'],original)['warning']
    with pytest.raises(ValueError,match='Keep My Premise'):story_ideas.develop_custom(s['id'],original)
    chosen=story_ideas.develop_custom(s['id'],{**original,'keep_premise':True})
    ep=core.episode(chosen['episode_id']);assert ep['data']['user_story_input']['premise']==original['premise']
    assert ep['data']['idea']['title']==original['title'] and ep['data']['genre_selection']['primary_genre_id']=='romance'

def test_legacy_ten_idea_schema_is_unchanged(store):
    run=creative.start_task('ideas',{})
    with core.db() as c:row=c.execute('SELECT request FROM runs WHERE id=?',(run['run_id'],)).fetchone()
    body=json.loads(json.loads(row['request'])['messages'][1]['content'])
    assert body['idea_count']==10 and body['output_json_schema']['properties']['ideas']['minItems']==10

def test_automatic_invalid_batch_gets_one_bounded_regeneration(store,monkeypatch):
    s=session();calls=[]
    def generate(config,messages,schema,root,runid,cancel):
        payload=json.loads(messages[1]['content']);data=concept_batch(payload);calls.append((runid,messages))
        if len(calls)==1:data['ideas'].pop()
        return data
    monkeypatch.setattr(providers,'generate',generate)
    monkeypatch.setenv('ODD_AI_PROVIDER','codex_cli')
    # Run synchronously for deterministic assertions; production still uses the normal executor.
    original=creative.start_task
    monkeypatch.setattr(creative,'start_task',lambda task,body,**kw:original(task,body,background=False,workspace=kw['workspace']))
    result=story_ideas.start_batch(s['id'],dict(idempotency_key=uuid.uuid4().hex))
    assert len(calls)==2 and result['status']=='SUCCEEDED'
    assert 'repair_feedback' in json.loads(calls[1][1][1]['content'])
    assert len(story_ideas.session_details(s['id'])['batches'][0]['result']['ideas'])==5

def test_manual_cancellation_closes_import_without_losing_previous_inputs(store):
    s=session();batch,run,payload=queued(s)
    assert creative.cancel_run(run['id'])['status']=='CANCELLED'
    with pytest.raises(ValueError,match='closed'):creative.complete_run(run['id'],concept_batch(payload),manual=True)
    assert story_ideas.session_details(s['id'])['batches'][0]['status']=='CANCELLED'
    assert not (story_ideas._root(s['id'])/'batches'/f"{batch['batch_id']}.json").exists()

def test_cross_session_selection_is_rejected(store):
    a=session();batch,run,payload=queued(a);data=concept_batch(payload);creative.complete_run(run['id'],data,manual=True)
    b=session()
    with pytest.raises(ValueError,match='does not belong'):story_ideas.select_story(b['id'],batch['batch_id'],data['ideas'][0]['idea_id'])
    with core.db() as c:assert c.execute('SELECT count(*) FROM episodes').fetchone()[0]==0

def test_provider_confirmation_and_idempotent_recovery(store,monkeypatch):
    s=session();key=uuid.uuid4().hex
    with pytest.raises(ValueError,match='provider changed'):story_ideas.start_batch(s['id'],dict(idempotency_key=key,expected_provider='codex_cli'))
    first=story_ideas.start_batch(s['id'],dict(idempotency_key=key,expected_provider='manual'))
    monkeypatch.setenv('ODD_AI_PROVIDER','codex_cli')
    recovered=story_ideas.start_batch(s['id'],dict(idempotency_key=key,expected_provider='manual'))
    assert recovered['run_id']==first['run_id'] and recovered['status']=='AWAITING_MANUAL'

@pytest.mark.parametrize('code,expected_calls',[('INVALID_OUTPUT',2),('AUTHENTICATION',1),('USAGE_LIMIT',1),('ISOLATION_UNAVAILABLE',1)])
def test_regeneration_is_bounded_and_never_retries_provider_authorization_errors(store,monkeypatch,code,expected_calls):
    s=session();calls=[]
    def failed(config,messages,schema,root,runid,cancel):
        calls.append(runid);raise providers.ProviderError('Synthetic provider failure',code)
    monkeypatch.setattr(providers,'generate',failed);monkeypatch.setenv('ODD_AI_PROVIDER','codex_cli')
    original=creative.start_task
    monkeypatch.setattr(creative,'start_task',lambda task,body,**kw:original(task,body,background=False,workspace=kw['workspace']))
    with pytest.raises(ValueError,match='Synthetic provider failure'):story_ideas.start_batch(s['id'],dict(idempotency_key=uuid.uuid4().hex))
    assert len(calls)==expected_calls
    assert story_ideas.session_details(s['id'])['batches'][0]['status']=='FAILED'

def test_surprise_primary_never_duplicates_secondary(store):
    with pytest.raises(ValueError,match='secondary genre'):story_ideas.create_session(dict(category_group_id='romance_other',surprise=True,secondary_genre_id='romance'))
    s=story_ideas.create_session(dict(category_group_id='comedy_dark_comedy',surprise=True,secondary_genre_id='comedy'))
    assert s['selection']['primary_genre_id'] in ('dark_comedy','dark_irony')

def test_saved_batch_recovers_after_interrupted_index_commit(store):
    s=session();batch,run,payload=queued(s);data=story_ideas.validate_result(run,concept_batch(payload))
    story_ideas.save_result(run,data,json.loads(run['provenance']))
    original=(story_ideas._root(s['id'])/'batches'/f"{batch['batch_id']}.json").read_bytes()
    # Simulate the immutable file having committed before the controller's SQLite update.
    creative.complete_run(run['id'],data,manual=True)
    assert (story_ideas._root(s['id'])/'batches'/f"{batch['batch_id']}.json").read_bytes()==original
    assert story_ideas.session_details(s['id'])['batches'][0]['status']=='SUCCEEDED'

def test_restart_recovers_unregistered_preparation_without_model_replay(store):
    from services.api.file_writer import EpisodeWriter
    s=session();s['batches'].append(dict(id='B'+uuid.uuid4().hex,number=1,idempotency_key=uuid.uuid4().hex,created=core.now(),status='PREPARING',run_ids=[]))
    EpisodeWriter(story_ideas._root(s['id'])).json('session.json',s)
    story_ideas.recover_pending_sessions()
    recovered=story_ideas.session_details(s['id'])['batches'][0]
    assert recovered['status']=='FAILED' and 'interrupted' in recovered['error']
    with core.db() as c:assert c.execute('SELECT count(*) FROM runs').fetchone()[0]==0
