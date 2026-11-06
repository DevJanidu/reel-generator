"""Controller-owned genre sessions. All creative execution uses the existing pinned provider path."""
import copy
import itertools
import json
import re
import secrets
import uuid
from difflib import SequenceMatcher
from . import core,genres,snapshots
from .file_writer import EpisodeWriter,episode_lock
from .idea_models import SessionSelection,BatchRequest,CustomStory,GenreIdeas,CRITERIA

def _root(session_id):
    if not re.fullmatch(r'[a-f0-9]{32}',session_id):raise ValueError('Invalid idea session ID')
    with core.db() as c:row=c.execute('SELECT path FROM idea_sessions WHERE id=?',(session_id,)).fetchone()
    if not row:raise ValueError('Idea session not found')
    root=core.STORE/row['path']
    if root.parent!=core.STORE/'episodes/_ideas' or root.name!='OF_G'+session_id:raise ValueError('Invalid idea session registration')
    EpisodeWriter(root)
    return root

def create_session(payload):
    choice=SessionSelection.model_validate(payload)
    taxonomy=genres.load();group=next((g for g in taxonomy['groups'] if g['id']==choice.category_group_id),None)
    if group is None:raise ValueError('Unknown category group')
    if choice.surprise:
        if choice.primary_genre_id:raise ValueError('Surprise selection must not also specify a primary genre')
        candidates=[g for g in group['genres'] if g['id']!=choice.secondary_genre_id]
        if not candidates:raise ValueError('The secondary genre must differ from a primary genre available in this group')
        primary=secrets.choice(candidates)['id']
    else:primary=choice.primary_genre_id
    group,genre=genres.resolve(taxonomy,choice.category_group_id,primary)
    secondary=genres.genre_by_id(taxonomy,choice.secondary_genre_id) if choice.secondary_genre_id else None
    if choice.secondary_genre_id and (secondary is None or secondary['id']==primary):raise ValueError('Choose a different valid secondary genre')
    sid=uuid.uuid4().hex;relative='episodes/_ideas/OF_G'+sid;root=core.STORE/relative
    root.mkdir(parents=True,exist_ok=False);snapshots.bootstrap(root)
    selection=dict(generation_mode='category',category_group_id=group['id'],category_group=group['name'],primary_genre_id=genre['id'],primary_genre=genre['name'],
                   secondary_genre_id=choice.secondary_genre_id,secondary_genre=secondary['name'] if secondary else None,
                   genre_definition=genre['description'],surprise=choice.surprise,taxonomy_version=taxonomy['version'],idea_count=5,
                   audience='US-primary',format='cinematic_2d_still_story',story_brand='ODD FRAME')
    state=dict(schema_version='2.0',id=sid,created=core.now(),selection=selection,batches=[],selected_stories=[],custom_selections={})
    EpisodeWriter(root).json('session.json',state,replace=False)
    with core.db() as c:c.execute('INSERT INTO idea_sessions(id,path,created,updated) VALUES (?,?,?,?)',(sid,relative,state['created'],state['created']))
    return session_details(sid)

def list_sessions():
    with core.db() as c:rows=[dict(r) for r in c.execute('SELECT id FROM idea_sessions ORDER BY created DESC LIMIT 100')]
    results=[]
    for row in rows:
        state=core.read_json(EpisodeWriter(_root(row['id'])).path('session.json'))
        results.append(dict(id=state['id'],created=state['created'],selection=state['selection'],batch_count=len(state['batches'])))
    return results

def recover_pending_sessions():
    """Controller startup only: repair the file/index gap without replaying model usage."""
    with core.db() as c:ids=[r['id'] for r in c.execute('SELECT id FROM idea_sessions')]
    for sid in ids:
        root=_root(sid);writer=EpisodeWriter(root)
        with episode_lock(root,'idea-session'):
            state=core.read_json(writer.path('session.json'));changed=False
            for batch in state['batches']:
                if batch.get('run_id') or batch['status']!='PREPARING':continue
                with core.db() as c:rows=c.execute("SELECT id,status,request FROM runs WHERE workspace=? AND task='genre_ideas'",(str(root),)).fetchall()
                matches=[r for r in rows if json.loads(json.loads(r['request'])['messages'][1]['content']).get('batch_id')==batch['id']]
                if len(matches)==1:batch.update(run_id=matches[0]['id'],run_ids=[matches[0]['id']],status=matches[0]['status'])
                else:batch.update(status='FAILED',error='Request preparation was interrupted before a provider job was registered. Confirm a new batch to continue.')
                changed=True
            if changed:writer.json('session.json',state)

def session_details(sid):
    root=_root(sid);writer=EpisodeWriter(root);state=core.read_json(writer.path('session.json'));out=copy.deepcopy(state)
    for batch in out['batches']:
        if batch.get('run_id'):
            with core.db() as c:row=c.execute('SELECT status,stage,error,created,provider FROM runs WHERE id=?',(batch['run_id'],)).fetchone()
            if row:
                batch.update(dict(row))
                if row['error']:
                    from .providers import redact
                    batch['error']=redact(row['error'])
            validation=writer.path(f".production/runs/{batch['run_id']}/import_validation.json")
            if validation.exists():
                issue=core.read_json(validation)
                if not issue['valid']:batch['validation_error']=issue['error']
        path=writer.path('batches/'+batch['id']+'.json')
        if path.exists():batch['result']=core.read_json(path)
    return out

def _history(root,exclude_batch=None):
    state=core.read_json(root/'session.json');concepts=[]
    for batch in state['batches']:
        if batch['id']==exclude_batch:continue
        path=EpisodeWriter(root).path('batches/'+batch['id']+'.json')
        if path.exists():concepts.extend(core.read_json(path)['ideas'])
    return concepts

def schema(payload):
    result=GenreIdeas.model_json_schema();result['properties']['category_group_id']['const']=payload['category_group_id'];result['properties']['primary_genre_id']['const']=payload['primary_genre_id']
    concept=result['$defs']['StoryConcept'];concept['properties']['category_group_id']['const']=payload['category_group_id'];concept['properties']['primary_genre_id']['const']=payload['primary_genre_id']
    concept['properties']['idea_id']['enum']=[payload['batch_id']+'-'+str(i) for i in range(1,6)]
    concept['properties']['secondary_genre_id']={'type':'string','const':payload['secondary_genre_id']} if payload.get('secondary_genre_id') else {'type':'null'}
    return result

def start_batch(sid,payload,retry_of=None):
    from .creative import start_task,run_event
    request=BatchRequest.model_validate(payload);root=_root(sid);writer=EpisodeWriter(root)
    with episode_lock(root,'idea-session'):
        state=core.read_json(writer.path('session.json'))
        for batch in state['batches']:
            if batch['idempotency_key']==request.idempotency_key:
                current=next(b for b in session_details(sid)['batches'] if b['id']==batch['id'])
                return dict(session_id=sid,batch_id=batch['id'],run_id=batch.get('run_id'),status=current['status'])
        if request.expected_provider and request.expected_provider!=core.settings()['provider']:raise ValueError('The AI provider changed. Review the confirmation with the current provider before generating.')
        with core.db() as c:
            active=c.execute("SELECT id FROM runs WHERE workspace=? AND status IN ('QUEUED','RUNNING','AWAITING_MANUAL')",(str(root),)).fetchone()
        if active:raise ValueError('Finish, import or cancel the current batch before requesting another five ideas')
        if len(state['batches'])>=20:raise ValueError('This session has 20 preserved batches. Start a new session to continue.')
        bid='B'+uuid.uuid4().hex;selection=state['selection']
        entry=dict(id=bid,number=len(state['batches'])+1,idempotency_key=request.idempotency_key,created=core.now(),status='PREPARING',run_ids=[])
        state['batches'].append(entry);writer.json('session.json',state)
        prior=_history(root)
        body=dict(**selection,session_id=sid,batch_id=bid,prior_concepts=[{k:c[k] for k in ('idea_id','title','logline','premise','main_characters','central_conflict','ending_direction')} for c in prior])
        try:
            result=start_task('genre_ideas',body,background=True,workspace=root,expected_provider=request.expected_provider)
        except (OSError,ValueError) as exc:
            entry.update(status='FAILED',error=str(exc));writer.json('session.json',state);raise
        entry.update(run_id=result['run_id'],run_ids=[result['run_id']],status=result['status']);writer.json('session.json',state)
        if retry_of:run_event(result['run_id'],'job.retry','New batch explicitly requested after a failed attempt',retry_of=retry_of)
        with core.db() as c:c.execute('UPDATE idea_sessions SET updated=? WHERE id=?',(core.now(),sid))
        return dict(session_id=sid,batch_id=bid,**result)

_STOP=set('a an the and or to of in on at with for from its his her their is was were be by that this as it he she they one when but then must has have who can into'.split())
def _tokens(text):return set(re.findall(r'[a-z0-9]+',text.lower()))-_STOP
def _similarity(a,b):
    x,y=_tokens(a),_tokens(b)
    return max(len(x&y)/max(1,len(x|y)),SequenceMatcher(None,' '.join(sorted(x)),' '.join(sorted(y))).ratio())

def near_duplicate(a,b):
    if re.sub(r'\W+','',a['title'].casefold())==re.sub(r'\W+','',b['title'].casefold()):return True
    premise=_similarity(a['logline']+' '+a['premise'],b['logline']+' '+b['premise'])
    conflict=_similarity(a['central_conflict'],b['central_conflict'])
    relationships=_similarity(' '.join(a['main_characters']),' '.join(b['main_characters']))
    return premise>.86 or (.5*premise+.35*conflict+.15*relationships)>.76 or (conflict>.94 and premise>.43)

def validate_result(run,result):
    payload=json.loads(json.loads(run['request'])['messages'][1]['content']);sid=payload['session_id'];root=_root(sid)
    if str(root)!=run['workspace']:raise ValueError('Idea result workspace does not match its registered session')
    data=GenreIdeas.model_validate(result).model_dump();selection=core.read_json(root/'session.json')['selection']
    if data['category_group_id']!=selection['category_group_id'] or data['primary_genre_id']!=selection['primary_genre_id']:raise ValueError('The response changed the confirmed genre identity')
    expected={payload['batch_id']+'-'+str(i) for i in range(1,6)}
    if {c['idea_id'] for c in data['ideas']}!=expected:raise ValueError('Five unique batch-scoped idea IDs are required')
    for concept in data['ideas']:
        if any(concept[k]!=selection[k] for k in ('category_group_id','primary_genre_id','secondary_genre_id')):raise ValueError('Every concept must retain the confirmed primary and secondary genre')
        if {a['criterion'] for a in concept['quality_audit']}!=set(CRITERIA) or any(a['assessment']!='ready' for a in concept['quality_audit']):raise ValueError('Complete the ten editorial checks and revise weak concepts before returning them')
        if any(len(x.strip())<3 for x in concept['main_characters']):raise ValueError('Provide meaningful main character descriptions')
    from .creative import run_event
    run_event(run['id'],'output.validating','Five complete concepts validated; checking premises, character relationships and conflicts')
    prior=_history(root,exclude_batch=payload['batch_id'])
    for a,b in itertools.combinations(data['ideas'],2):
        if near_duplicate(a,b):raise ValueError('Near-duplicate concepts within this batch: vary premises, character relationships and central conflicts')
    for concept in data['ideas']:
        for previous in prior:
            if near_duplicate(concept,previous):raise ValueError('A concept is too close to a previous session batch; develop a different premise and conflict')
    return data

def save_result(run,data,evidence):
    payload=json.loads(json.loads(run['request'])['messages'][1]['content']);root=_root(payload['session_id']);writer=EpisodeWriter(root)
    record=dict(**data,batch_id=payload['batch_id'],generated_at=core.now(),provider=run['provider'],master_prompt=evidence['master_prompt'],
                skill_versions={s['id']:s['version'] for s in evidence['skills']},taxonomy=evidence.get('genre_taxonomy'),
                diversity_check='Heuristic comparison of titles, premises, relationships and conflicts; not a guarantee of originality',
                editorial_assessments='Model editorial judgments, not verified popularity scores')
    with episode_lock(root,'idea-session'):
        relative='batches/'+payload['batch_id']+'.json'
        if writer.path(relative).exists():
            existing=core.read_json(writer.path(relative))
            if any(existing.get(key)!=value for key,value in data.items()):raise ValueError('A different validated batch already exists; saved concepts cannot be overwritten')
        else:writer.json(relative,record,replace=False)
    from .creative import run_event
    run_event(run['id'],'file.saved','Five validated story concepts saved',file='batches/'+payload['batch_id']+'.json',completed=5,total=5)

def retry_run(runid):
    with core.db() as c:run=c.execute('SELECT request,status FROM runs WHERE id=?',(runid,)).fetchone()
    if not run or run['status'] not in ('FAILED','CANCELLED'):raise ValueError('Only failed or cancelled batches can be retried')
    payload=json.loads(json.loads(run['request'])['messages'][1]['content'])
    return start_batch(payload['session_id'],dict(idempotency_key=uuid.uuid4().hex),retry_of=runid)

def _begin_story(root,state,key,idea,concept,custom_input=None,source_batch=None,expected_provider=None):
    from .creative import create_episode,start_task
    existing=next((x for x in state['selected_stories'] if x['selection_key']==key),None)
    if existing:return dict(episode_id=existing['episode_id'],run_id=core.episode(existing['episode_id'])['data'].get('pending_run'))
    ep=create_episode(idea)
    context=dict(**state['selection'],session_id=state['id'],selection_key=key)
    if source_batch:
        context.update(idea_batch_id=source_batch['batch_id'],generation_timestamp=source_batch['generated_at'],provider=source_batch['provider'],
                       master_prompt=source_batch['master_prompt'],skill_versions=source_batch['skill_versions'],taxonomy=source_batch['taxonomy'])
    ep=core.update_episode(ep['id'],genre_selection=context,story_concept=concept,user_story_input=custom_input)
    state['selected_stories'].append(dict(selection_key=key,episode_id=ep['id'],title=idea['title'],selected_at=core.now()))
    EpisodeWriter(root).json('session.json',state)
    request=start_task('script',dict(idea=ep['data']['idea']),ep['id'],background=True,expected_provider=expected_provider)
    core.update_episode(ep['id'],pending_run=request['run_id'])
    return dict(episode_id=ep['id'],**request)

def select_story(sid,bid,idea_id):
    root=_root(sid);writer=EpisodeWriter(root)
    if not re.fullmatch(r'B[a-f0-9]{32}',bid):raise ValueError('Invalid batch ID')
    with episode_lock(root,'idea-session'):
        state=core.read_json(writer.path('session.json'));batch=next((b for b in state['batches'] if b['id']==bid),None)
        if batch is None:raise ValueError('Batch does not belong to this session')
        with core.db() as c:run=c.execute('SELECT status FROM runs WHERE id=?',(batch['run_id'],)).fetchone()
        if not run or run['status']!='SUCCEEDED':raise ValueError('Wait for the validated batch before selecting a story')
        saved=core.read_json(writer.path('batches/'+bid+'.json'))
        concept=next((i for i in saved['ideas'] if i['idea_id']==idea_id),None)
        if concept is None:raise ValueError('Concept does not belong to this batch')
        idea=dict(title=concept['title'],genre=state['selection']['primary_genre'],premise=concept['premise'],visual_hook=concept['opening_visual_hook'],narration_hook=concept['logline'],
                  conflict=concept['central_conflict'],curiosity=concept['central_conflict'],emotion=concept['target_emotion'],ending_type=concept['ending_direction'],character_type='; '.join(concept['main_characters']),feasibility=concept['visual_feasibility'])
        return _begin_story(root,state,bid+':'+idea_id,idea,concept,source_batch=saved)

def premise_warning(selection,title,premise):
    text=(title+' '+premise).lower();genre=selection['primary_genre_id']
    explicit_horror=any(t in text for t in ('a horror story','pure horror','haunted','serial killer','terrifying monster'))
    if genre in ('comedy','romance','wholesome_heartwarming') and explicit_horror:
        return f"This premise includes horror elements that may conflict with {selection['primary_genre']}. You can keep your exact premise and ask for a genre-aware development, or change the genre."
    if genre in ('comedy','dark_comedy') and any(t in text for t in ('without humor','no jokes','no comedy')):return 'The premise explicitly excludes humor. Keep the premise deliberately or choose another genre.'
    if genre=='romance' and any(t in text for t in ('no love','without romance')):return 'The premise explicitly excludes romance. Keep the premise deliberately or choose another genre.'
    return None

def check_custom(sid,payload):
    custom=CustomStory.model_validate(payload);state=core.read_json(_root(sid)/'session.json')
    return dict(warning=premise_warning(state['selection'],custom.title,custom.premise),note='This is a limited wording check, not an authoritative genre assessment. Your supplied title and premise are preserved.')

def develop_custom(sid,payload):
    custom=CustomStory.model_validate(payload);root=_root(sid);writer=EpisodeWriter(root)
    if custom.expected_provider and custom.expected_provider!=core.settings()['provider']:raise ValueError('The AI provider changed. Review the confirmation again before developing the story.')
    with episode_lock(root,'idea-session'):
        state=core.read_json(writer.path('session.json'));selection=state['selection']
        warning=premise_warning(selection,custom.title,custom.premise)
        if warning and not custom.keep_premise:raise ValueError(warning+' Confirm Keep My Premise before continuing.')
        premise=custom.premise or f"Owner supplied the title '{custom.title}'. Develop this specific title as {selection['primary_genre']}; the premise has not yet been written."
        idea=dict(title=custom.title,genre=selection['primary_genre'],premise=premise,visual_hook='Pending AI development of the owner-supplied story.',narration_hook='Pending script writing.',
                  conflict='Pending development from the owner input.',curiosity='Pending development from the owner input.',emotion=selection['primary_genre'],ending_type='Genre-appropriate; not yet generated',character_type='To be developed from the owner input',feasibility='Static 2D production requirements apply; creative feasibility awaits development.')
        return _begin_story(root,state,'custom:'+custom.idempotency_key,idea,None,dict(title=custom.title,premise=custom.premise,keep_premise=custom.keep_premise,warning=warning),expected_provider=custom.expected_provider)
