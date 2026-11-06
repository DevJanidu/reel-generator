import json
import os
import re
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from .core import ROOT, STORE, now, sha, db, episode, epdir, update_episode, textfile, write_json, settings
from .skills import model_request, load_skills
from .models import Ideas, Idea, Script, Package, Flow
from .idea_models import GenreIdeas
from .file_writer import EpisodeWriter,episode_lock
from . import snapshots,providers,styles
from .activity import emit

def run_event(runid, kind, message, **details):
    with db() as c: row=c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone()
    if row and row['workspace']:
        details.setdefault('status',row['status'])
        return emit(row['workspace'],runid,row['episode_id'],row['provider'],row['task'],kind,message,**details)

_executor=ThreadPoolExecutor(max_workers=4,thread_name_prefix='odd-frame-creative-controller')
_condition=threading.Condition()
_active=0
_cancellations={}

TASKS={'ideas':('01_IDEA_GENERATION.md',Ideas),'script':('02_SCRIPT_WRITING.md',Script),
       'genre_ideas':('01_IDEA_GENERATION.md',GenreIdeas),'review':('03_SCRIPT_REVIEW.md',Script),'prepare':('04_CHARACTER_BIBLE.md',Package)}

def clean_words(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.lower().replace('’',"'"))

def _style_notes(scene):
    notes='\nTransition in: '+scene.get('transition_in','cut')
    if scene.get('transition_reason'):notes+=' ('+scene['transition_reason']+')'
    if scene.get('emphasis_phrase'):notes+='\nGlow emphasis phrase: '+scene['emphasis_phrase']
    return notes

def create_episode(idea):
    idea=Idea.model_validate(idea).model_dump()
    slug=re.sub(r'[^a-z0-9]+','-',idea['title'].lower()).strip('-')[:65] or 'story'
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        cursor=c.execute('INSERT INTO episodes(title,status,data,updated) VALUES (?,?,?,?)',
                         (idea['title'],'DRAFT',json.dumps(dict(idea=idea,script=None,approval=None)),now()))
        eid=cursor.lastrowid
        code=f'OF_R{eid:03d}'
        path=f'episodes/{code}_{slug}'
        directory=STORE/path
        # Collision-safe allocation: an existing unregistered folder is never overwritten.
        directory.mkdir(parents=True,exist_ok=False)
        c.execute('UPDATE episodes SET code=?,path=? WHERE id=?',(code,path,eid))
    for folder in ['00_brief','01_script','02_characters','03_storyboard','04_google_flow/batches',
                   '05_assets/images','05_assets/narration','05_assets/subtitles','05_assets/music',
                   '06_edit/remotion','06_edit/previews','07_export/final','reports','.production/locks','.production/temp','.production/logs']:
        (directory/folder).mkdir(parents=True,exist_ok=True)
    snapshots.bootstrap(directory)
    textfile(directory/'00_brief/STORY_BRIEF.md', '# '+idea['title']+'\n\n'+idea['premise'])
    # New episodes inherit the global editing default ONCE, from their own pinned snapshot; later global changes never apply.
    style=styles.global_default_style(styles.snapshot_dir(directory))
    return update_episode(eid,'DRAFT',dependent_stages='PENDING',style=style,message='Selected story; script awaits creation and approval')

def persist_provenance(eid, runid, evidence):
    if not eid:
        return
    path=epdir(episode(eid))/'reports/SKILL_PROVENANCE.json'
    with episode_lock(epdir(episode(eid)),'mutation'):
        existing=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(episode_id=episode(eid)['code'],brand='ODD FRAME',runs=[])
        existing['runs'].append(dict(run_id=runid,**evidence))
        write_json(path,existing)

def start_task(task, payload, eid=None,background=False,workspace=None,expected_provider=None,retry_of=None):
    if eid:
        with episode_lock(epdir(episode(eid)),'schedule',blocking=False):
            return _start_task(task,payload,eid,background,workspace,expected_provider,retry_of)
    return _start_task(task,payload,eid,background,workspace,expected_provider,retry_of)

def _start_task(task, payload, eid=None,background=False,workspace=None,expected_provider=None,retry_of=None):
    import time
    context_started=time.monotonic()
    stage, schema=TASKS[task]
    config=settings()
    if expected_provider and config['provider']!=expected_provider:raise ValueError('The AI provider changed. Review the confirmation again before generating.')
    if eid:
        if retry_of and task=='prepare' and episode(eid)['data'].get('package'):raise ValueError('A validated production package already exists; use the asset/edit workflow instead of regenerating it')
        with db() as c:
            active=c.execute("SELECT id FROM runs WHERE episode_id=? AND status IN ('QUEUED','RUNNING')",(eid,)).fetchone()
        if active:raise ValueError('An AI operation is already active for this episode; cancel it or wait before retrying')
        root=epdir(episode(eid))
        if not (root/'.production/provenance.json').exists():snapshots.bootstrap(root)
    elif workspace is not None:
        root=Path(workspace)
        if root.parent!=STORE/'episodes/_ideas' or not root.name.startswith('OF_G'):raise ValueError('Invalid category generation workspace')
    else:
        root=STORE/'episodes'/'_ideas'/('OF_I'+uuid.uuid4().hex)
        root.mkdir(parents=True,exist_ok=False);snapshots.bootstrap(root)
    source=snapshots.source_root(root)
    if eid and episode(eid)['data'].get('genre_selection'):
        context=episode(eid)['data']
        payload={**payload,'genre_context':context['genre_selection'],'selected_story_concept':context.get('story_concept'),'user_story_input':context.get('user_story_input')}
    if task=='genre_ideas':
        from .story_ideas import schema as genre_schema
        response_schema=genre_schema(payload)
    else:response_schema=schema.model_json_schema()
    payload={**payload,'output_json_schema':response_schema}
    if task=='ideas':
        payload.setdefault('generation_mode','legacy_general');payload.setdefault('idea_count',10)
        with db() as c:
            payload['recent_ideas']=[json.loads(r['data'])['idea'] for r in c.execute('SELECT data FROM episodes ORDER BY id DESC LIMIT 20')]
    if task=='prepare':
        ep=episode(eid)
        loaded,current_rules=load_skills(source)
        frozen=ep['data'].get('approval',{})
        current_hashes={d['id']:d['sha256'] for d in loaded}
        if frozen.get('skill_hashes')!=current_hashes or frozen.get('override_version')!=current_rules['version']:
            update_episode(eid,'BLOCKED',error='Skills changed after approval. Reconcile source changes before regenerating derived files; approved narration was preserved.')
            raise ValueError('Skills changed after approval. Use Reconcile Skills to record reviewed changes, preserving approved narration, then Retry.')
        payload['coordinated_stage_instructions']={name:(source/'prompts'/name).read_text(encoding='utf-8') for name in
            ['05_STORYBOARD.md','06_FLOW_IMAGE_PROMPTS.md','07_RETENTION_AUDIT.md','11_PUBLISHING.md']}
    messages,evidence=model_request(stage,payload,config,root=source)
    runid=str(uuid.uuid4())
    evidence.update(job_group_id=runid,attempt_number=1,retry_of=None,timeout_seconds=config.get('timeout_seconds',300))
    evidence['context_preparation_seconds']=round(time.monotonic()-context_started,3)
    if retry_of:
        with db() as c:previous=c.execute('SELECT provenance,status FROM runs WHERE id=?',(retry_of,)).fetchone()
        if not previous or previous['status'] not in ('FAILED','CANCELLED'):raise ValueError('Only failed or cancelled attempts can be retried')
        prior=json.loads(previous['provenance']);evidence.update(job_group_id=prior.get('job_group_id',retry_of),attempt_number=prior.get('attempt_number',1)+1,retry_of=retry_of)
        with db() as c:others=c.execute('SELECT id,status,provenance FROM runs WHERE workspace=? AND task=?',(str(root),task)).fetchall()
        for other in others:
            meta=json.loads(other['provenance'])
            if meta.get('job_group_id')==evidence['job_group_id'] and meta.get('attempt_number',1)>=evidence['attempt_number']:
                if other['status'] in ('QUEUED','RUNNING','AWAITING_MANUAL'):return dict(run_id=other['id'],status=other['status'],job_group_id=evidence['job_group_id'],attempt_number=meta['attempt_number'])
                raise ValueError('Retry the latest failed attempt; this attempt has already been superseded')
    evidence['episode_id']=episode(eid)['code'] if eid else None
    if eid:
        evidence['script_approval']=episode(eid)['data'].get('approval')
    request=dict(model=config['model'],messages=messages,max_tokens=config['output_tokens'],response_format={'type':'json_object'})
    evidence['pinned_input_root']=str(source)
    evidence['execution_workspace']=str(root)
    evidence['requested_schema_sha256']=sha(json.dumps(response_schema,sort_keys=True))
    writer=EpisodeWriter(root)
    writer.json(f'.production/runs/{runid}/request.json',dict(request=request,provenance=evidence))
    with db() as c:
        c.execute('INSERT INTO runs(id,episode_id,task,status,request,provenance,created,workspace,stage,progress,provider) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                  (runid,eid,task,'AWAITING_MANUAL' if config['provider']=='manual' else 'QUEUED',json.dumps(request),json.dumps(evidence),now(),str(root),'Loading skills',.05,config['provider']))
    persist_provenance(eid,runid,evidence)
    if eid:update_episode(eid,{'prepare':'PREPARING','script':'SCRIPTING','review':'SCRIPT_REVIEW'}.get(task,'PREPARING'),error=None,pending_run=runid)
    if retry_of:run_event(runid,'job.retry','Explicit retry accepted; previous attempt retained',retry_of=retry_of)
    if task=='genre_ideas':run_event(runid,'category.confirmed',f"Category confirmed: {payload['category_group']} / {payload['primary_genre']}")
    run_event(runid,'job.queued','Request queued; waiting for an available provider slot')
    run_event(runid,'skills.validated','All four complete pinned skills, master and stage instructions validated')
    run_event(runid,'ai.request.prepared','Complete schema-bound request saved')
    if config['provider']=='manual':
        run_progress(runid,'Awaiting manual structured response',.1,status='AWAITING_MANUAL')
        if eid:
            update_episode(eid,'AWAITING_MANUAL',pending_run=runid,error=None,message=f'Import {task} JSON using the exported full instruction bundle')
        return dict(run_id=runid,status='AWAITING_MANUAL',message='Download full AI request, use your own AI tool, then import its JSON response. No AI call was simulated.')
    _cancellations[runid]=threading.Event()
    if background:
        _executor.submit(execute_run,runid,config,messages,response_schema,root,True)
        return dict(run_id=runid,status='QUEUED',job_group_id=evidence['job_group_id'],attempt_number=evidence['attempt_number'],message=f'Full skills loaded; {task} queued using {config["provider"]}')
    return execute_run(runid,config,messages,response_schema,root)

def run_progress(runid,stage,progress,status=None):
    with db() as c:
        row=c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone()
        if not row:return
        c.execute('UPDATE runs SET stage=?,progress=?,status=? WHERE id=?',(stage,progress,status or row['status'],runid))
    if row['workspace']:
        EpisodeWriter(row['workspace']).json(f'.production/runs/{runid}/state.json',dict(id=runid,episode_id=row['episode_id'],task=row['task'],status=status or row['status'],stage=stage,progress=progress,updated=now()))
    run_event(runid,'stage.completed' if status=='SUCCEEDED' else 'ai.activity',stage,status=status or row['status'])

def execute_run(runid,config,messages,schema,root,background=False):
    global _active
    cancel=_cancellations.setdefault(runid,threading.Event())
    with _condition:
        while _active>=config.get('max_concurrent_jobs',1):
            if cancel.is_set():
                fail_run(runid,'Generation cancelled');_cancellations.pop(runid,None)
                return dict(run_id=runid,status='CANCELLED')
            _condition.wait(.25)
        _active+=1
    released=False
    try:
        with episode_lock(root,'creative',blocking=False):
            run_event(runid,'job.started','Starting authorized provider execution')
            run_progress(runid,'Preparing AI request',.15,status='RUNNING')
            if cancel.is_set():raise providers.ProviderError('Generation cancelled','CANCELLED')
            run_progress(runid,'Checking provider authentication and native isolation',.3)
            with db() as c:run=dict(c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone())
            for attempt in range(2 if run['task']=='genre_ideas' else 1):
                provider_run=runid if attempt==0 else runid+'-repair-1'
                provider_config={**config,'activity_run_id':runid} if run['task']=='genre_ideas' else config
                result=None
                try:
                    result=providers.generate(provider_config,messages,schema,root,provider_run,cancel)
                    if run['task']!='genre_ideas':break
                    EpisodeWriter(root).json(f'.production/runs/{runid}/attempts/{attempt+1:02d}-response.json',result,replace=False)
                    if cancel.is_set():raise providers.ProviderError('Generation cancelled','CANCELLED')
                    from .story_ideas import validate_result
                    validate_result(run,result)
                    break
                except (ValueError,providers.ProviderError) as validation_error:
                    if run['task']!='genre_ideas' or attempt:raise
                    if isinstance(validation_error,providers.ProviderError) and validation_error.code!='INVALID_OUTPUT':raise
                    run_event(runid,'output.repair','Concept validation failed; starting one bounded schema-aware regeneration')
                    body=json.loads(json.loads(run['request'])['messages'][1]['content'])
                    body.update(repair_feedback=str(validation_error)[:2400],rejected_response=result,repair_instruction='Return a complete replacement batch of exactly five valid, distinct concepts. Retain the confirmed genre and all batch-scoped IDs; do not pad with placeholders.')
                    messages,repair_evidence=model_request(TASKS['genre_ideas'][0],body,config,root=snapshots.source_root(root))
                    EpisodeWriter(root).json(f'.production/runs/{runid}/attempts/02-request.json',dict(messages=messages,provenance=repair_evidence))
            if cancel.is_set():raise providers.ProviderError('Generation cancelled','CANCELLED')
            run_progress(runid,'Validating model response',.8)
            run_event(runid,'output.validating','Checking structured output against the stage contract')
        with _condition:_active-=1;_condition.notify_all();released=True
        return complete_run(runid,result,background=background)
    except Exception as exc:
        fail_run(runid,getattr(exc,'code',type(exc).__name__)+': '+str(exc))
        # Background failures persist exact provider diagnosis; sync callers also receive it.
        if not background:raise ValueError('AI request failed: '+str(exc)) from exc
        return dict(run_id=runid,status='FAILED',error=str(exc),error_code=getattr(exc,'code','PROVIDER_FAILED'))
    finally:
        if not released:
            with _condition:_active-=1;_condition.notify_all()
        _cancellations.pop(runid,None)

def cancel_run(runid):
    with db() as c: row=c.execute('SELECT status,task,workspace FROM runs WHERE id=?',(runid,)).fetchone()
    if row and row['task']=='genre_ideas' and row['status']=='AWAITING_MANUAL':
        with episode_lock(row['workspace'],'commit'):
            with db() as c:current=c.execute('SELECT status FROM runs WHERE id=?',(runid,)).fetchone()
            if current['status']!='AWAITING_MANUAL':raise ValueError('This generation is no longer waiting for manual input')
            fail_run(runid,'Generation cancelled by the owner before manual import')
        return dict(run_id=runid,status='CANCELLED')
    if not row or row['status'] not in ('QUEUED','RUNNING'):raise ValueError('This generation is no longer active')
    if runid not in _cancellations:raise ValueError('No active AI execution for this run')
    _cancellations[runid].set()
    return dict(run_id=runid,status='CANCELLING')

def stop_creative():
    for event in list(_cancellations.values()):event.set()

def fail_run(runid,error):
    with db() as c:row=c.execute('SELECT workspace,episode_id FROM runs WHERE id=?',(runid,)).fetchone()
    if row and row['episode_id']:
        with episode_lock(row['workspace'],'schedule'):
            return _fail_run(runid,error)
    return _fail_run(runid,error)

def _fail_run(runid,error):
    from .job_errors import diagnosis
    from datetime import datetime
    with db() as c:prior=c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone()
    if not prior or prior['status'] in ('FAILED','CANCELLED','SUCCEEDED'):return
    diagnostic={**diagnosis(error), 'job_id':runid,'episode_id':prior['episode_id'],'provider':prior['provider'],
                'failed_stage':prior['stage'],'failed_at':now(),
                'elapsed_seconds':max(0,round((datetime.fromisoformat(now())-datetime.fromisoformat(prior['created'])).total_seconds(),1))}
    if prior['workspace']:
        from .activity import generation_progress
        latest=generation_progress(prior['workspace'],runid,'RUNNING',prior['stage'],prior['provider'])
        diagnostic.update(failed_stage=latest['message'],last_activity_at=latest['last_event_at'])
        try:EpisodeWriter(prior['workspace']).json(f'.production/runs/{runid}/failure.json',dict(public=diagnostic,technical=providers.redact(str(error))[-3500:]))
        except OSError:pass
    status='CANCELLED' if 'cancelled' in error.lower() else 'FAILED'
    with db() as c:
        c.execute('UPDATE runs SET status=?,error=?,stage=? WHERE id=?',(status,error,'Cancelled' if status=='CANCELLED' else 'Failed',runid))
        row=c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone()
    if row and row['workspace']:
        EpisodeWriter(row['workspace']).json(f'.production/runs/{runid}/state.json',dict(id=runid,episode_id=row['episode_id'],status=status,error=error,stage=row['stage'],progress=row['progress'],updated=now()))
        run_event(runid,'job.cancelled' if status=='CANCELLED' else 'ai.failed',
                  diagnostic['message'],status=status)
    if row and row['episode_id'] and episode(row['episode_id'])['data'].get('pending_run') in (None,runid):
        update_episode(row['episode_id'],'FAILED',error=diagnostic['category']+': '+diagnostic['message'])

def complete_run(runid,result,manual=False,background=False):
    with db() as c:row=c.execute('SELECT workspace FROM runs WHERE id=?',(runid,)).fetchone()
    if not row:raise ValueError('Unknown generation run')
    if row['workspace']:
        with episode_lock(row['workspace'],'commit'):
            return _complete_run(runid,result,manual,background)
    return _complete_run(runid,result,manual,background)

def _complete_run(runid,result,manual=False,background=False):
    with db() as c:
        row=c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone()
    if not row:
        raise ValueError('Unknown generation run')
    run=dict(row)
    if run['status']=='SUCCEEDED':
        return dict(run_id=runid,status='SUCCEEDED',result=json.loads(run['result']))
    # Every import is bound to the exact mandatory full request and detects stale references.
    source=snapshots.source_root(Path(run['workspace'])) if run.get('workspace') else ROOT
    docs,rules=load_skills(source)
    evidence=json.loads(run['provenance'])
    if [d['sha256'] for d in docs] != [d['sha256'] for d in evidence['skills']] or rules['version']!=evidence['override_version']:
        raise ValueError('Skills changed since this request. Export a new request; approved script remains frozen.')
    if sha((source/'prompts/00_MASTER_PROMPT.md').read_text(encoding='utf-8'))!=evidence['master_prompt']['sha256']:
        raise ValueError('Master prompt changed; create a new request')
    task=run['task']; eid=run['episode_id']
    if task=='genre_ideas' and run['status'] not in ('AWAITING_MANUAL','QUEUED','RUNNING'):raise ValueError('This idea batch is closed. Confirm a new batch instead of importing into a failed or cancelled request.')
    if task=='genre_ideas':
        from .story_ideas import validate_result,save_result
        try:data=validate_result(run,result)
        except ValueError as exc:
            if manual:
                detail='; '.join('.'.join(map(str,e['loc']))+': '+e['msg'] for e in exc.errors(include_input=False)) if hasattr(exc,'errors') else str(exc)
                EpisodeWriter(run['workspace']).json(f'.production/runs/{runid}/import_validation.json',dict(valid=False,error=providers.redact(detail),at=now()))
                run_event(runid,'output.rejected','Imported concepts failed validation. Correct the structured response and import again; no batch was saved.')
            raise
        save_result(run,data,evidence)
        if manual:EpisodeWriter(run['workspace']).json(f'.production/runs/{runid}/import_validation.json',dict(valid=True,at=now()))
    else:data=TASKS[task][1].model_validate(result).model_dump()
    if eid and task in ('script','review') and episode(eid)['data'].get('approval'):
        raise ValueError('Approved narration is locked. Revoke approval before creating another version.')
    if task=='prepare':
        run_progress(runid,'Saving validated production package',.9)
        run_event(runid,'output.saving','Package schema validated; saving production artifacts')
        try:
            writer=EpisodeWriter(run['workspace'])
            if evidence.get('retry_of'):
                for base in ('02_characters','03_storyboard','04_google_flow'):
                    for path in writer.path(base).rglob('*'):
                        if path.is_file() and path.suffix.lower() in ('.md','.json','.txt'):
                            rel=str(path.relative_to(writer.root)).replace('\\','/')
                            writer.bytes(f'.production/runs/{runid}/before-retry/{rel}',writer.path(rel).read_bytes(),replace=False)
            populate(eid,data,evidence)
        except OSError as exc:raise providers.ProviderError('Could not persist the production package','ARTIFACT_PERSISTENCE') from exc
    elif task in ('script','review'):
        ep=episode(eid)
        update_episode(eid,'SCRIPT_REVIEW' if task=='script' else 'AWAITING_APPROVAL',script=data,pending_run=None,error=None)
        textfile(epdir(ep)/'01_script/SCRIPT.md',data['narration'])
    if run.get('workspace'):EpisodeWriter(run['workspace']).json(f'.production/runs/{runid}/validated_result.json',data)
    run_event(runid,'file.saved','Validated structured result saved',file=f'.production/runs/{runid}/validated_result.json')
    if eid:
        public_files = ['01_script/SCRIPT.md'] if task in ('script','review') else ['02_characters/CHARACTER_BIBLE.md','03_storyboard/STORYBOARD.md','04_google_flow/IMAGE_JOBS.json'] if task=='prepare' else []
        for filename in public_files:
            if (epdir(episode(eid))/filename).is_file():run_event(runid,'file.saved','Generated file verified',file=filename)
    with db() as c:
        c.execute('UPDATE runs SET status=?,result=?,error=NULL WHERE id=?',('SUCCEEDED',json.dumps(data),runid))
    run_progress(runid,'Five story ideas ready for selection' if task=='genre_ideas' else 'Completed' if task not in ('script','review') else 'Waiting for script approval' if task=='review' else 'Script generated; retention review next',1,status='SUCCEEDED')
    run_event(runid,'job.completed','Validated stage complete. '+('Select one of the five concepts in Ideas to begin its script.' if task=='genre_ideas' else 'Approve the reviewed script to continue.' if task=='review' else 'Add still images, narration and SRT subtitles in Asset Manager.' if task=='prepare' else 'Continue in the episode workspace.'),status='SUCCEEDED')
    if manual:
        evidence['external_execution']='Manual import: document delivery verified; model identity/compliance user-attested, not independently observed'
        persist_provenance(eid,runid+'-import',evidence)
    if task=='script':
        return start_task('review',dict(idea=episode(eid)['data']['idea'],draft=data),eid,background=background)
    return dict(run_id=runid,status='SUCCEEDED',result=data)

def approve(eid,narration,brief=None,background=False):
    with episode_lock(epdir(episode(eid)),'commit'):
        return _approve(eid,narration,brief,background)

def _approve(eid,narration,brief=None,background=False):
    ep=episode(eid); data=ep['data']
    if data.get('approval'):
        if sha(narration)!=data['approval']['sha256']:
            raise ValueError('This script is already approved with different wording. Revoke explicitly first.')
        return dict(status=ep['status'],message='Existing approval retained; use Retry if preparation failed')
    if not data.get('script') or ep['status']!='AWAITING_APPROVAL':
        raise ValueError('Import or generate a reviewed draft before approval')
    docs,rules=load_skills(snapshots.source_root(epdir(ep)))
    if len(narration.strip())<30:
        raise ValueError('Narration is empty or too short')
    if brief is not None and len(brief.strip())<10:
        raise ValueError('Story brief must contain useful context')
    script={**data['script'],'narration':narration,'brief':brief if brief is not None else data['script']['brief']}
    approval=dict(version=data.get('previous_approval',{}).get('version',0)+1,sha256=sha(narration),timestamp=now(),approved_by='Disposable test harness (explicit test authorization)' if os.getenv('ODD_TEST_RUN')=='1' else 'local owner',auto_export=True,revoked=False,
                  skill_hashes={d['id']:d['sha256'] for d in docs},override_version=rules['version'],
                  owner_edited_after_review=sha(narration)!=sha(data['script']['narration']))
    update_episode(eid,'PREPARING',script=script,approval=approval,pending_run=None,error=None)
    directory=epdir(ep)
    textfile(directory/'01_script/SCRIPT.md',narration)
    textfile(directory/'01_script/narration.txt',narration)
    write_json(directory/'01_script/SCRIPT_APPROVAL.json',approval)
    textfile(directory/'00_brief/STORY_BRIEF.md','# '+ep['title']+'\n\n'+script['brief'])
    return start_task('prepare',dict(idea=data['idea'],approved_narration=narration,approval=approval),eid,background=background)

def approved(ep):
    approval=ep['data'].get('approval')
    if not approval or approval.get('revoked') or not approval['auto_export']:
        raise ValueError('Valid script approval/export authorization required')
    narration=(epdir(ep)/'01_script/narration.txt').read_bytes().decode('utf-8')
    if sha(narration)!=approval['sha256'] or sha(ep['data']['script']['narration'])!=approval['sha256']:
        raise ValueError('Approved narration hash mismatch')
    return approval

def populate(eid,package,evidence):
    ep=episode(eid); approval=approved(ep); directory=epdir(ep)
    # A different revision cannot fulfill an old pending preparation request.
    if evidence.get('script_approval',{}).get('sha256')!=approval['sha256']:
        raise ValueError('Preparation request references a different approved script')
    scenes=package['scenes']; chars={c['id']:c for c in package['characters']}
    if len(chars)!=len(package['characters']):
        raise ValueError('Duplicate character IDs')
    if [s['scene_id'] for s in scenes]!=[f'S{i+1:03d}' for i in range(len(scenes))]:
        raise ValueError('Scene IDs must be unique sequential S001, S002…')
    if clean_words(' '.join(s['narration_text'] for s in scenes))!=clean_words(ep['data']['script']['narration']):
        raise ValueError('Storyboard must cover the approved narration exactly once in original order')
    if len({a['criterion'] for a in package['retention']})!=10:
        raise ValueError('Retention rubric must cover all ten distinct criteria')
    # Existing scene IDs/images must not be silently replaced by retries or updated skills.
    old=ep['data'].get('package')
    if old and old!=package:
        raise ValueError('A package already exists. Reconciliation is required; existing scene assets were preserved.')
    # Style hints are requests, validated here: the first scene never transitions and an emphasis phrase must be
    # 1-4 contiguous words of that scene's own narration, otherwise it is dropped (never trusted blindly).
    for i,scene in enumerate(scenes):
        if i==0:scene['transition_in']='hard_cut'
        phrase=clean_words(scene.get('emphasis_phrase','') or '')
        words=clean_words(scene['narration_text'])
        if phrase and (len(phrase)>4 or not any(words[j:j+len(phrase)]==phrase for j in range(len(words)-len(phrase)+1))):
            scene['emphasis_phrase']=''
    jobs=[]
    for scene in scenes:
        if any(cid not in chars for cid in scene['character_ids']):
            raise ValueError('Undefined character in '+scene['scene_id'])
        for region in scene['protected_regions']:
            if region['x']+region['width']>1 or region['y']+region['height']>1:
                raise ValueError('Protected region exceeds image bounds')
        descriptions='\n'.join(chars[cid]['name']+': '+chars[cid]['description'] for cid in scene['character_ids']) or 'No characters visible in this detail still.'
        prompt=f'''Create one original STATIC vertical 9:16 cinematic 2D ODD FRAME story illustration.
STORY BEAT: {scene['beat']}
CHARACTERS: {descriptions}
EXPRESSIONS AND POSES: {scene['expression_pose']}
LOCATION AND LAYOUT: {scene['location']}
APPROVED PROPS AND STATES: {scene['props']}
FRAMING AND COMPOSITION: {scene['framing']}
FIRST LOOK TARGET: {scene['focus']}. This matters because {scene['focus_reason']}.
MIDNIGHT GOLD: #14171C charcoal and #41464E slate quiet environment, #7D838B lifted details, #F1EBDD readable features. ONE purposeful #FFD43B attention zone: {scene['yellow_placement']}. Tiny #FFF2B0 highlights only. No unrelated saturated accents or blanket gold filter. Matte yellow does not glow.
LIGHTING: {scene['lighting']}
CONTINUITY LOCKS: {scene['continuity']}
STRICT 2D: hand-drawn dark ink outlines, simplified expressive faces, readable silhouettes, flat local colors, limited stepped shading, restrained paper texture. Genre-appropriate mood, not automatic horror. All scenery and lighting illustrated.
EXCLUDE: photorealism, 3D, CGI, realistic human faces, extra limbs, inconsistent characters, altered props, random glowing objects, gibberish text, captions, logos and watermarks. STILL IMAGE ONLY. No generated animation or video.'''
        if re.search(r'\b(TODO|TBD|PLACEHOLDER)\b|\[[A-Z_ ]{3,}\]',prompt):
            raise ValueError('Unresolved placeholder in scene prompt')
        jobs.append(dict(job_id=scene['scene_id']+'_IMG',scene_id=scene['scene_id'],type='image',prompt=prompt,source_image=None,output_name=scene['scene_id']))
    flow=Flow(episode_id=ep['code'],jobs=jobs).model_dump()
    textfile(directory/'02_characters/CHARACTER_BIBLE.md','# Character Bible\n\n'+'\n\n'.join(f"## {c['id']} — {c['name']}\n{c['description']}\n\nDesire: {c['desire']}" for c in chars.values()))
    textfile(directory/'02_characters/CONTINUITY_MATRIX.md',package['continuity_matrix'])
    textfile(directory/'03_storyboard/STORYBOARD.md','# PROVISIONAL STORYBOARD — exact timing awaits narration/SRT\n\n'+'\n\n'.join(f"## {s['scene_id']}\nNarration: {s['narration_text']}\n\n{s['beat']}\n\n{s['framing']}\nGold: {s['yellow_placement']}\nContinuity: {s['continuity']}"+_style_notes(s) for s in scenes))
    import csv,io
    stream=io.StringIO(); writer=csv.writer(stream); writer.writerow(['scene_id','timing_status','estimated_seconds','narration'])
    for s in scenes:
        writer.writerow([s['scene_id'],'PROVISIONAL',round(len(clean_words(s['narration_text']))/2.5,2),s['narration_text']])
    textfile(directory/'03_storyboard/SCENE_TIMELINE.csv',stream.getvalue())
    textfile(directory/'03_storyboard/STYLE_AND_SCENE_LOCKS.md','# Static Midnight Gold scene locks\n\n'+package['continuity_matrix']+'\n\nTypography only motion. No SFX. Required center captions.')
    audit='# Editorial retention review — script/storyboard evidence, not actual audience data\n\n'+'\n\n'.join(f"## {a['criterion']}: {a['rating']}\n{a['evidence']}\n\nRecommendation: {a['recommendation']}" for a in package['retention'])
    textfile(directory/'03_storyboard/RETENTION_AUDIT.md',audit)
    write_json(directory/'04_google_flow/IMAGE_JOBS.json',flow)
    textfile(directory/'04_google_flow/IMAGE_PROMPTS.md','\n\n'.join(f"## {j['scene_id']}\n{j['prompt']}" for j in jobs))
    for i in range(0,len(jobs),10):
        write_json(directory/f'04_google_flow/batches/batch_{i//10+1:02d}.json',{**flow,'jobs':jobs[i:i+10]})
    write_json(directory/'03_storyboard/ASSET_MANIFEST.json',dict(episode_id=ep['code'],images=[s['scene_id'] for s in scenes],audio_sources=['narration','instrumental'],subtitle_required=True))
    write_json(directory/'06_edit/caption_design.json',dict(font='Barlow Condensed',weight=800,color='#FFFFFF',outline='#000000',required=True,animation=styles.effective_style(ep)['profile']['captions']['entrance'],style_profile=styles.effective_style(ep)['profile_id'],positions={s['scene_id']:s['caption_y'] for s in scenes}))
    textfile(directory/'06_edit/MUSIC_DIRECTION.md',package['music_direction']+'\n\nUser-supplied instrumental only. No SFX. Rights evidence required from user; never inferred.')
    textfile(directory/'07_export/PUBLISHING.md',package['publishing'])
    update_episode(eid,'AWAITING_ASSETS',package=package,pending_run=None,error=None,dependent_stages='COMPLETE',message='Complete preproduction validated; waiting for user assets')
