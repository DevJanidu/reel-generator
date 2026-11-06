import json
import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from .core import ROOT, STORE, db, init_db, settings, episode, epdir, update_episode, read_json, now, write_json,controller_token,sync_index
from .skills import skill_status, model_request
from .creative import create_episode, start_task, complete_run, approve, approved
from .media import validate_assets, IMAGE_EXT, AUDIO_EXT
from .worker import start_worker, stop, enqueue,secure_validate
from . import providers,isolation,snapshots
from .file_writer import EpisodeWriter,episode_lock,no_links
from .creative import cancel_run,run_progress,stop_creative

@asynccontextmanager
async def lifespan(app):
    init_db(); (STORE/'episodes').mkdir(parents=True,exist_ok=True)
    from .story_ideas import recover_pending_sessions
    recover_pending_sessions()
    thread=start_worker()
    yield
    stop_creative();stop.set(); thread.join(timeout=2)
    from . import studio
    studio.stop_all()

app=FastAPI(title='ODD FRAME Reel Workflow Station',version='1.0.0',lifespan=lifespan)

@app.get('/api/activity')
def activity_jobs(episode_id:int|None=None):
    from .activity import collect
    return collect(episode_id)

@app.get('/api/activity/stream')
async def activity_stream(request:Request, episode_id:int|None=None):
    import asyncio
    from .activity import collect,encode_cursor,decode_cursor
    cursor=decode_cursor(request.headers.get('last-event-id') or request.query_params.get('cursor',''))
    async def stream():
        nonlocal cursor
        yield 'retry: 2500\n\n'
        while not await request.is_disconnected():
            jobs=await asyncio.to_thread(collect,episode_id)
            retained={j['job_id'] for j in jobs}
            cursor={k:v for k,v in cursor.items() if k in retained}
            for job in jobs:
                events=job['events']; previous=cursor.get(job['job_id'],0)
                if events and previous and previous<events[0]['sequence']-1:
                    yield 'event: reset\ndata: {}\n\n'
                for event in events:
                    if event['sequence']>previous:
                        cursor[job['job_id']]=event['sequence']
                        yield f'id: {encode_cursor(cursor)}\nevent: activity\ndata: {json.dumps(event)}\n\n'
            yield ': heartbeat\n\n'
            await asyncio.sleep(1)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.middleware('http')
async def local_only(request:Request,call_next):
    # Local station: refuse cross-origin mutations and DNS-rebinding Host values.
    host=request.headers.get('host','').split(':')[0]
    if host not in ('127.0.0.1','localhost','testserver'):
        return JSONResponse({'detail':'Local station accepts localhost only'},status_code=403)
    origin=request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin:
        from urllib.parse import urlparse
        parsed=urlparse(origin)
        if parsed.hostname not in ('localhost','127.0.0.1') or parsed.port not in (8123,5173,int(os.getenv('ODD_PORT','8123'))):
            return JSONResponse({'detail':'Cross-origin write rejected'},status_code=403)
    if request.method not in ('GET','HEAD','OPTIONS'):
        import secrets
        supplied=request.headers.get('x-odd-controller','')
        if not secrets.compare_digest(supplied,controller_token()):
            return JSONResponse({'detail':'Controller authorization required. Open the dashboard using scripts/start.ps1. Episode workers cannot access this capability.'},status_code=401)
    return await call_next(request)

@app.exception_handler(ValueError)
async def value_error(request,exc):
    return JSONResponse({'detail':str(exc)},status_code=422)

@app.exception_handler(FileNotFoundError)
async def missing_file(request,exc):
    return JSONResponse({'detail':str(exc)},status_code=422)

def _overlay_job(job,local):
    """The SQLite row owns job status/error; the episode-local JSON only supplies live
    stage/progress written by the isolated worker (its own status copy goes stale)."""
    if job['status'] in ('QUEUED','RUNNING'):
        for key in ('stage','progress','updated'):
            if key in local:job[key]=local[key]

@app.get('/api/status')
def status():
    sync_index()
    with db() as c:
        counts={r['status']:r['n'] for r in c.execute('SELECT status,count(*) n FROM episodes GROUP BY status')}
        jobs=[dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT 500')]
    for job in jobs:
        local=epdir(episode(job['episode_id']))/f'.production/jobs/{job["id"]}.json'
        if local.exists():_overlay_job(job,read_json(local))
    return dict(brand='ODD FRAME',counts=counts,jobs=jobs,skills=skill_status(),settings=settings(),
                tools={tool:shutil.which(tool) is not None for tool in ['node','ffmpeg','ffprobe']},
                isolation=isolation.status(),remotion_installed=(ROOT/'node_modules/@remotion/renderer').exists(),master_exists=(ROOT/'prompts/00_MASTER_PROMPT.md').exists())

@app.get('/api/skills')
@app.post('/api/skills/validate')
def skills():
    return skill_status()

@app.get('/api/master')
def master():
    import re
    content=(ROOT/'prompts/00_MASTER_PROMPT.md').read_text(encoding='utf-8')
    return dict(content=content,version=re.search(r'^Version:\s*([0-9.]+)',content,re.M).group(1))

@app.get('/api/settings')
def get_settings():
    return settings()

@app.put('/api/settings')
def put_settings(payload:dict):
    allowed={'provider','base_url','model','context_tokens','output_tokens','music_preferences','timeout_seconds','max_concurrent_jobs'}
    if set(payload)-allowed:
        raise ValueError('Secrets and fixed production rules cannot be changed through settings')
    if payload.get('provider','manual') not in providers.PROVIDERS:
        raise ValueError('Supported providers: codex_cli, claude_cli, manual, openai-compatible')
    from urllib.parse import urlparse
    if 'base_url' in payload and urlparse(payload['base_url']).scheme not in ('https','http'):
        raise ValueError('Provider endpoint must be HTTP(S)')
    for key in ('context_tokens','output_tokens'):
        if key in payload and not 512<=int(payload[key])<=2000000:
            raise ValueError('Invalid token budget')
    if 'timeout_seconds' in payload and not 15<=int(payload['timeout_seconds'])<=1800:raise ValueError('AI timeout must be 15–1800 seconds')
    if 'max_concurrent_jobs' in payload and not 1<=int(payload['max_concurrent_jobs'])<=4:raise ValueError('AI concurrency must be 1–4, with per-workspace OS verification')
    with db() as c:
        for key,value in payload.items():
            c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)',(key,json.dumps(value)))
    return settings()

@app.get('/api/episodes')
def list_episodes():
    sync_index()
    with db() as c:
        return [dict(id=r['id'],code=r['code'],title=r['title'],status=r['status'],updated=r['updated']) for r in c.execute('SELECT * FROM episodes ORDER BY id DESC')]

@app.post('/api/episodes')
def select(payload:dict):
    return create_episode(payload)

@app.get('/api/episodes/{eid}')
def detail(eid:int):
    ep=episode(eid)
    with db() as c:
        ep['history']=[dict(r) for r in c.execute('SELECT * FROM events WHERE episode_id=? ORDER BY id DESC LIMIT 1000',(eid,))]
        ep['runs']=[dict(r) for r in c.execute('SELECT id,task,status,error,created,stage,progress,provider FROM runs WHERE episode_id=? ORDER BY created DESC',(eid,))]
        ep['jobs']=[dict(r) for r in c.execute('SELECT * FROM jobs WHERE episode_id=? ORDER BY id DESC',(eid,))]
    directory=epdir(ep)
    ep['history']=list(reversed(read_json(directory/'.production/history.json'))) if (directory/'.production/history.json').exists() else ep['history']
    for job in ep['jobs']:
        local=directory/f'.production/jobs/{job["id"]}.json'
        if local.exists():_overlay_job(job,read_json(local))
    ep['files']=[str(p.relative_to(directory)).replace('\\','/') for p in directory.rglob('*') if p.is_file() and not p.name.endswith('.tmp') and '.production' not in p.relative_to(directory).parts]
    ep['isolation']=isolation.status(directory)
    ep['input_snapshot']=read_json(directory/'.production/provenance.json') if (directory/'.production/provenance.json').exists() else None
    ep['style_info']=_style_summary(ep)
    ep['studio']=_studio_summary(ep)
    try:snapshots.validate(directory);ep['pinned_inputs_valid']=True
    except (OSError,ValueError) as exc:ep['pinned_inputs_valid']=False;ep['pinned_input_error']=str(exc)
    ep['asset_report']=read_json(directory/'reports/ASSET_VALIDATION.json') if (directory/'reports/ASSET_VALIDATION.json').exists() else None
    ep['timeline']=read_json(directory/'06_edit/timeline.json') if (directory/'06_edit/timeline.json').exists() else None
    ep['flow']=read_json(directory/'04_google_flow/IMAGE_JOBS.json') if (directory/'04_google_flow/IMAGE_JOBS.json').exists() else None
    ep['provenance']=read_json(directory/'reports/SKILL_PROVENANCE.json') if (directory/'reports/SKILL_PROVENANCE.json').exists() else None
    return ep

@app.post('/api/episodes/{eid}/editor/prepare')
def prepare_editor(eid:int):
    from .editor import load
    ep=episode(eid)
    if (epdir(ep)/'06_edit/editor_state.json').exists():return dict(status='EDIT_READY',revision=load(eid)['state']['revision'])
    return dict(job_id=enqueue(eid,'draft'))

@app.post('/api/episodes/{eid}/editor/rebuild')
def rebuild_editor(eid:int,payload:dict|None=None):
    ep=episode(eid);approved(ep);directory=epdir(ep);writer=EpisodeWriter(directory)
    with episode_lock(directory,'media',blocking=False),episode_lock(directory,'editor'):
        with db() as c:
            if c.execute("SELECT id FROM jobs WHERE episode_id=? AND status IN ('QUEUED','RUNNING')",(eid,)).fetchone():raise ValueError('A production job is already active')
        state=read_json(writer.path('06_edit/editor_state.json'))
        archive=f'06_edit/revisions/plan-{state["revision"]:06d}.json'
        if not writer.path(archive).exists():writer.json(archive,read_json(writer.path('06_edit/edit_plan.json')),replace=False)
        # Keep the last complete revision readable until the new worker commits its revision.
        from .editor import provision_runtime
        runtime=provision_runtime(directory)
        writer.json('06_edit/edit_plan.json',dict(version=1,runtime=runtime))
        state['ready']=False;writer.json('06_edit/editor_state.json',state)
        from .worker import _enqueue
        return dict(job_id=_enqueue(eid,'draft',rebuild=True,replace_studio=bool((payload or {}).get('replace_studio_edits'))))

@app.get('/api/episodes/{eid}/editor')
def get_editor(eid:int):
    from .editor import load
    return load(eid)

@app.get('/api/episodes/{eid}/editor/revisions/{revision}')
def editor_revision(eid:int,revision:int):
    from .editor import load
    saved=load(eid)
    if revision not in saved['revisions']:raise ValueError('Unknown saved revision')
    return read_json(EpisodeWriter(epdir(episode(eid))).path(f'06_edit/revisions/{revision:06d}.json'))

@app.put('/api/episodes/{eid}/editor')
def save_editor(eid:int,payload:dict):
    from .editor import save
    return save(eid,payload)

@app.post('/api/episodes/{eid}/editor/render')
def render_editor(eid:int,payload:dict):
    from .editor import load
    saved=load(eid)
    if payload.get('revision')!=saved['state']['revision']:raise ValueError('Save or reload the current revision before rendering')
    return dict(job_id=enqueue(eid,'render'))

# ------------------------------------------------------------------ official Remotion Studio
STUDIO_CAPABILITIES = dict(
    visual=[
        'Props panel (saved into Root.tsx): narration gain 0-2x, music gain 0-2x, music fade in/out, extra ducking, caption glow strength',
        'Timeline: every still (inside "STORY — stills + transitions"), caption phrase, narration and music is a named, selectable sequence',
        'Timeline: drag/trim a caption sequence to change its timing (written into Episode.tsx)',
        'Sequence inspector: opacity, background, border, crop, layout, duplicate, split, unwrap (provided by Studio)',
    ],
    source_only=[
        'Caption text, animation preset (wave/glow/smooth/impact/soft), gold emphasis, vertical position, enter/exit frames: edit Episode.tsx',
        'Scene transitions: every boundary is a commented TransitionSeries.Transition in Episode.tsx (crossfade() or dipToCharcoal() with transitionTiming(frames)); hard and graphic-match cuts have no element. Studio has no drag-and-drop transition editor',
        'Changing a still duration inside the TransitionSeries shifts the later stills (captions/audio stay put): the checker warns when a scene change leaves its narration frame and blocks a wrong total length',
    ],
    blocked=[
        'Image movement (pan, zoom, rotate, scale, offset, keyframes) and extra audio/sound effects are rejected at launch and at export',
    ],
    not_verified=['Split/duplicate/drag-to-move behaviour of Studio itself was not tested by ODD FRAME'],
)


def _studio_summary(ep):
    from . import studio
    directory = epdir(ep)
    manifest = studio.manifest(directory)
    out = dict(exists=bool(manifest), capabilities=STUDIO_CAPABILITIES)
    if not manifest:
        out['hint'] = 'Run Auto Edit; the station then builds the complete Remotion Studio project.'
        return out
    try:
        studio.validate_project(directory)
        out['valid'] = True
    except ValueError as exc:
        out.update(valid=False, problem=str(exc))
    check = studio.check_source(directory) if (studio.studio_dir(directory) / 'src/Episode.tsx').is_file() else dict(errors=[], warnings=[])
    out.update(composition_id=manifest['composition_id'], created=manifest['created'], style=manifest.get('style'),
               remotion_version=manifest.get('remotion_version'), source_editor_revision=manifest.get('source_editor_revision'),
               scene_sequences=len(check.get('scenes', [])), caption_sequences=check.get('captions'),
               source_errors=check['errors'], source_warnings=check['warnings'],
               owner_edited_files=studio.owner_changes(directory), session=studio.session(ep['id']),
               starting=studio.is_starting(ep['id']), launch=studio.launch_state(directory),
               folder=f'episodes/{directory.name}/{studio.STUDIO_DIR}')
    return out


@app.get('/api/episodes/{eid}/studio')
def studio_status(eid: int):
    return _studio_summary(episode(eid))


@app.post('/api/episodes/{eid}/studio/generate')
def studio_generate(eid: int, payload: dict):
    """Build the Studio project from the latest saved Auto Edit revision (deterministic, no AI call).

    Never replaces Studio edits unless replace_my_edits is true; the previous source is archived either way."""
    from . import studio
    ep = episode(eid)
    approved(ep)
    directory = epdir(ep)
    _style_busy(ep)
    state_path = directory / '06_edit/editor_state.json'
    if not state_path.exists():
        raise ValueError('Run Auto Edit first: the station needs the prepared timeline and measured audio.')
    state = read_json(state_path)
    if not state.get('ready'):
        raise ValueError('An Auto Edit rebuild is still in progress.')
    props = read_json(directory / f'06_edit/revisions/{state["revision"]:06d}.json')
    with episode_lock(directory, 'media', blocking=False), episode_lock(directory, 'editor'):
        studio.stop(eid)
        manifest = studio.generate(directory, props, ep['data']['package']['scenes'], ep['code'],
                                   force=bool(payload.get('replace_my_edits')), source_revision=state['revision'])
    update_episode(eid, ep['status'], message='Remotion Studio project generated. Open it in Remotion Studio.')
    return dict(composition_id=manifest['composition_id'])


@app.post('/api/episodes/{eid}/studio/open')
def studio_open(eid: int):
    from . import studio
    ep = episode(eid)
    approved(ep)
    if ep['status'] in ('QUEUED', 'RENDERING'):
        raise ValueError('A render is in progress; open Studio when it finishes.')
    if not studio.manifest(epdir(ep)):
        raise ValueError('There is no Studio project yet. Run Auto Edit or Generate Studio project first.')
    return studio.begin_start(eid, epdir(ep), max_concurrent=int(settings().get('max_concurrent_jobs', 2)) or 2)


@app.post('/api/episodes/{eid}/studio/stop')
def studio_stop(eid: int):
    from . import studio
    episode(eid)
    return dict(stopped=studio.stop(eid))


@app.post('/api/episodes/{eid}/studio/render')
def studio_render(eid: int):
    """Final export from the exact Studio project the owner reviewed (its saved source is authoritative)."""
    ep = episode(eid)
    approved(ep)
    return dict(job_id=enqueue(eid, 'studio-render'))


@app.post('/api/ideas/generate')
def ideas(payload:dict):
    if payload.get('generation_mode')=='category':
        from .story_ideas import start_batch
        if set(payload)-{'generation_mode','session_id','idempotency_key','expected_provider'}:raise ValueError('Category generation uses the confirmed session selection; arbitrary genre overrides are rejected')
        return start_batch(payload.get('session_id',''),dict(idempotency_key=payload.get('idempotency_key',''),expected_provider=payload.get('expected_provider')))
    return start_task('ideas',payload,background=True)

@app.get('/api/genres')
def story_genres():
    from .genres import load
    return load()

@app.get('/api/idea-sessions')
def idea_sessions():
    from .story_ideas import list_sessions
    return list_sessions()

@app.post('/api/idea-sessions')
def idea_session_create(payload:dict):
    from .story_ideas import create_session
    return create_session(payload)

@app.get('/api/idea-sessions/{sid}')
def idea_session_detail(sid:str):
    from .story_ideas import session_details
    return session_details(sid)

@app.post('/api/idea-sessions/{sid}/batches')
def idea_batch_create(sid:str,payload:dict):
    from .story_ideas import start_batch
    return start_batch(sid,payload)

@app.post('/api/idea-sessions/{sid}/batches/{bid}/select')
def idea_story_select(sid:str,bid:str,payload:dict):
    from .story_ideas import select_story
    if set(payload)!={'idea_id'}:raise ValueError('Select one saved concept ID')
    return select_story(sid,bid,payload['idea_id'])

@app.post('/api/idea-sessions/{sid}/custom/check')
def custom_story_check(sid:str,payload:dict):
    from .story_ideas import check_custom
    return check_custom(sid,payload)

@app.post('/api/idea-sessions/{sid}/custom')
def custom_story_develop(sid:str,payload:dict):
    from .story_ideas import develop_custom
    return develop_custom(sid,payload)

@app.post('/api/episodes/{eid}/script')
def script(eid:int):
    ep=episode(eid)
    if ep['data'].get('approval'):
        raise ValueError('Approved script is locked')
    return start_task('script',dict(idea=ep['data']['idea']),eid,background=True)

@app.post('/api/episodes/{eid}/draft')
def draft(eid:int,payload:dict):
    from .models import Script
    ep=episode(eid)
    if ep['data'].get('approval'):
        raise ValueError('Approved script is locked')
    with db() as c:
        if c.execute("SELECT id FROM runs WHERE episode_id=? AND status IN ('QUEUED','RUNNING')",(eid,)).fetchone():raise ValueError('Cancel or finish the current AI generation before importing an owner draft')
    from .skills import load_skills
    load_skills(snapshots.source_root(epdir(ep)))
    data=Script.model_validate(payload).model_dump()
    return update_episode(eid,'AWAITING_APPROVAL',script=data,draft_source='Explicit user-authored/imported draft; AI review not claimed')

@app.post('/api/episodes/{eid}/approve')
def approval(eid:int,payload:dict):
    return approve(eid,payload['narration'],payload.get('brief'),background=True)

@app.post('/api/episodes/{eid}/revoke')
def revoke(eid:int):
    ep=episode(eid)
    if ep['status'] in ('QUEUED','RENDERING'):
        raise ValueError('Wait for the active job to finish before replacing a script; export may still be revoked with /cancel-export')
    if ep['data'].get('package'):
        raise ValueError('Prepared episodes retain immutable continuity. Create a new episode for a new script revision.')
    old=ep['data'].get('approval')
    return update_episode(eid,'AWAITING_APPROVAL',approval=None,previous_approval=old,pending_run=None)

@app.post('/api/episodes/{eid}/cancel-export')
def cancel_export(eid:int):
    ep=episode(eid); approval=ep['data'].get('approval')
    if not approval:
        raise ValueError('No approval exists')
    approval={**approval,'revoked':True,'revoked_at':now()}
    write_json(epdir(ep)/'01_script/SCRIPT_APPROVAL.json',approval)
    with db() as c:
        c.execute("UPDATE jobs SET status='FAILED',error='Export authorization revoked' WHERE episode_id=? AND status='QUEUED'",(eid,))
    return update_episode(eid,'BLOCKED',approval=approval,error='Export authorization revoked')

@app.post('/api/episodes/{eid}/retry')
def retry(eid:int):
    ep=episode(eid); approved(ep)
    if not ep['data'].get('package'):
        return start_task('prepare',dict(idea=ep['data']['idea'],approved_narration=ep['data']['script']['narration'],approval=ep['data']['approval']),eid,background=True)
    report=secure_validate(eid)
    if not report['valid']:
        raise ValueError('; '.join(report['errors']))
    state_path=epdir(ep)/'06_edit/editor_state.json'
    if state_path.exists():
        if not read_json(state_path).get('ready'):return rebuild_editor(eid)
        from .editor import needs_rebuild
        if needs_rebuild(eid,report):raise ValueError('Assets or style changed. Use Rebuild Draft before exporting again.')
        return dict(job_id=enqueue(eid,'render'))
    return dict(job_id=enqueue(eid))

@app.post('/api/episodes/{eid}/reconcile-skills')
def reconcile(eid:int):
    result=snapshots.validate(epdir(episode(eid)))
    return dict(message='Pinned inputs validated. Later global changes do not alter this episode.',snapshot=result)

@app.get('/api/runs')
def runs():
    with db() as c:
        return [dict(r) for r in c.execute('SELECT id,episode_id,task,status,error,created,stage,progress,provider FROM runs ORDER BY created DESC LIMIT 100')]

@app.get('/api/runs/{runid}/request')
def request_bundle(runid:str):
    with db() as c:
        run=c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone()
    if not run:
        raise HTTPException(404)
    request=json.loads(run['request'])
    return Response(json.dumps(dict(request=request,provenance=json.loads(run['provenance']),instructions='Use the complete messages with your AI tool. Return only JSON matching the output_json_schema in the user message. Import the result into this run.'),indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="odd-frame-{runid}.json"'})

@app.get('/api/runs/{runid}/result')
def run_result(runid:str):
    with db() as c:
        run=c.execute('SELECT result,error,status,stage,progress FROM runs WHERE id=?',(runid,)).fetchone()
    if not run:
        raise HTTPException(404)
    return dict(status=run['status'],error=run['error'],stage=run['stage'],progress=run['progress'],result=json.loads(run['result']) if run['result'] else None)

@app.post('/api/runs/{runid}/import')
def import_run(runid:str,payload:dict):
    return complete_run(runid,payload,manual=True)

@app.post('/api/episodes/{eid}/assets/refresh')
def refresh(eid:int):
    ep=episode(eid)
    if ep['status'] in ('QUEUED','RENDERING'):
        return dict(valid=True,message='Already queued or rendering')
    report=secure_validate(eid)
    if report['valid']:
        if (epdir(ep)/'06_edit/editor_state.json').exists():
            from .editor import needs_rebuild
            stale=needs_rebuild(eid,report)
            update_episode(eid,'EDIT_STALE' if stale else 'EDIT_READY',error=None)
            report['message']='Explicitly rebuild the draft to use changed assets/style; previous revisions are preserved.' if stale else 'Saved editable draft ready in Live Editor'
        else:enqueue(eid)
    else:update_episode(eid,'ASSETS_BLOCKED',asset_errors=report['errors'])
    return report

@app.post('/api/episodes/{eid}/assets/{kind}')
async def upload(eid:int,kind:str,request:Request):
    if kind not in ('images','narration','subtitles','music'):
        raise ValueError('Unknown asset type')
    ep=episode(eid); approved(ep)
    if ep['status'] in ('QUEUED','RENDERING'):
        raise ValueError('Uploads are blocked while rendering; wait for this job to finish')
    if not ep['data'].get('package'):
        raise ValueError('Complete preproduction before importing episode assets')
    # Starlette normally spills multipart uploads into global TEMP. Scope even parser spools
    # to this episode, without mutating process-wide tempfile globals across concurrent requests.
    from starlette.formparsers import MultiPartParser
    from tempfile import SpooledTemporaryFile
    spool_dir=EpisodeWriter(epdir(ep)).path('.production/temp/upload-spools');spool_dir.mkdir(parents=True,exist_ok=True)
    class ScopedParser(MultiPartParser):
        def on_headers_finished(self):
            super().on_headers_finished()
            if self._current_part.file is not None:
                previous=self._current_part.file.file
                replacement=SpooledTemporaryFile(max_size=self.spool_max_size,dir=spool_dir)
                self._current_part.file.file=replacement
                self._files_to_close_on_error.remove(previous);self._files_to_close_on_error.append(replacement);previous.close()
    form=await ScopedParser(request.headers,request.stream(),max_files=100,max_fields=10,max_part_size=512*1024*1024).parse()
    files=form.getlist('files')
    if not files:raise ValueError('Choose at least one file to import')
    directory=epdir(ep)/'05_assets'/kind
    allowed=IMAGE_EXT if kind=='images' else {'.srt'} if kind=='subtitles' else AUDIO_EXT
    imported=[]
    for file in files:
        name=file.filename or ''
        if '/' in name or '\\' in name or Path(name).name!=name or Path(name).suffix.lower() not in allowed:
            raise ValueError('Unsupported or unsafe asset filename: '+name)
        if kind=='images':
            if Path(name).stem.upper() not in {s['scene_id'] for s in ep['data']['package']['scenes']}:
                raise ValueError('Unknown scene image: '+name)
            name=Path(name).stem.upper()+Path(name).suffix.lower()
        writer=EpisodeWriter(epdir(ep));target=writer.path(f'05_assets/{kind}/{name}')
        if target.exists():
            raise ValueError(name+' already exists. Remove it explicitly before replacement.')
        temporary=writer.path(f'.production/temp/upload-{__import__("uuid").uuid4().hex}.upload');temporary.parent.mkdir(parents=True,exist_ok=True)
        size=0
        try:
            with temporary.open('wb') as handle:
                while chunk:=await file.read(1024*1024):
                    size+=len(chunk)
                    if size>512*1024*1024:
                        raise ValueError('Each asset must be below 512 MiB')
                    handle.write(chunk)
            with episode_lock(epdir(ep),'assets'):
                writer.bytes(f'05_assets/{kind}/{name}',temporary.read_bytes(),replace=False)
        finally:
            temporary.unlink(missing_ok=True)
        imported.append(name)
    await form.close()
    update_episode(eid,'AWAITING_ASSETS',error=None)
    return dict(imported=imported)

@app.delete('/api/episodes/{eid}/assets/{kind}/{name}')
def delete_asset(eid:int,kind:str,name:str):
    if kind not in ('images','narration','subtitles','music') or Path(name).name!=name or '\\' in name:
        raise ValueError('Invalid asset path')
    ep=episode(eid)
    if ep['status'] in ('QUEUED','RENDERING'):
        raise ValueError('Cannot remove assets during render')
    EpisodeWriter(epdir(ep)).delete(f'05_assets/{kind}/{name}')
    return update_episode(eid,'AWAITING_ASSETS',error=None)

@app.post('/api/episodes/{eid}/exports/delete')
def delete_exports(eid:int,payload:dict):
    """Owner-confirmed deletion of one or more finished exports of ONE episode.

    Only exports this episode recorded (by job id) can be named; each MP4 and its preview clip are removed from inside the
    episode's export folder through the safe writer (no traversal, links or directories). Script, stills, audio, Studio
    project and every other export are untouched. Never during a render. Irreversible, so `confirm` must be true."""
    if payload.get('confirm') is not True:
        raise ValueError('Deleting exports is permanent. Confirm the deletion.')
    ids=payload.get('job_ids')
    if not isinstance(ids,list) or not ids or len(ids)>200 or any(isinstance(i,bool) or not isinstance(i,int) for i in ids):
        raise ValueError('Choose the exports to delete (a list of export job ids).')
    ep=episode(eid)
    if ep['status'] in ('QUEUED','RENDERING'):
        raise ValueError('Cannot delete exports while a render is in progress')
    with db() as c:
        if c.execute("SELECT id FROM jobs WHERE episode_id=? AND status IN ('QUEUED','RUNNING')",(eid,)).fetchone():
            raise ValueError('A production job is active for this episode; wait for it to finish')
    known={e['job_id']:e for e in ep['data'].get('exports',[])}
    missing=[i for i in ids if i not in known]
    if missing:raise ValueError('Unknown export(s): '+', '.join(map(str,missing)))
    writer=EpisodeWriter(epdir(ep));removed=[];gone=[]
    for jid in dict.fromkeys(ids):
        entry=known[jid]
        for key,folder in (('path','07_export/final/'),('preview','06_edit/previews/')):
            rel=entry.get(key)
            if not rel:continue
            # Recorded paths are relative to the data root; convert to episode-relative and require the right folder.
            rel=str(rel).replace('\\','/');prefix=f'episodes/{epdir(ep).name}/'
            if not rel.startswith(prefix) or '..' in rel.split('/'):
                if key=='path':raise ValueError('Refusing to delete a file outside this episode: '+rel)
                continue
            rel=rel[len(prefix):]
            if not rel.startswith(folder) or not rel.lower().endswith('.mp4'):
                if key=='path':raise ValueError('Refusing to delete a file outside the export folder: '+rel)
                continue
            target=writer.path(rel)
            if target.is_file():writer.delete(rel);removed.append(rel)
            else:gone.append(rel)
    remaining=[e for e in ep['data'].get('exports',[]) if e['job_id'] not in set(ids)]
    history=list(ep['data'].get('export_deletions',[]))+[dict(at=now(),job_ids=list(dict.fromkeys(ids)),files=removed,already_missing=gone)]
    update_episode(eid,ep['status'],exports=remaining,export_deletions=history,error=None,
                   message=f"Deleted {len(set(ids))} export{'s' if len(set(ids))!=1 else ''}. Your script, stills, audio and Studio project were not touched.")
    return dict(deleted=sorted(set(ids)),files=removed,remaining=len(remaining),
                message=f"Deleted {len(set(ids))} export{'s' if len(set(ids))!=1 else ''}. Your script, stills, audio and Studio project were not touched.")

@app.post('/api/episodes/{eid}/music-rights')
def rights(eid:int,payload:dict):
    if not isinstance(payload.get('instrumental_confirmed'),bool) or not isinstance(payload.get('evidence',''),str):
        raise ValueError('Provide instrumental_confirmed boolean and rights evidence text')
    return update_episode(eid,music_rights=dict(instrumental_confirmed=payload['instrumental_confirmed'],evidence=payload.get('evidence',''),recorded_at=now()))

@app.put('/api/episodes/{eid}/music-level')
def music_level(eid:int,payload:dict):
    """Owner music-volume offset (dB relative to the automatic balance). Applied at the next mix."""
    ep=episode(eid);approved(ep)
    if ep['status'] in ('QUEUED','RENDERING'):
        raise ValueError('Wait for the current render to finish (or cancel it) before changing the music level')
    try:offset=float(payload.get('offset_db'))
    except (TypeError,ValueError):raise ValueError('Provide offset_db as a number')
    if not -12<=offset<=6:raise ValueError('Music level offset must be between -12 and +6 dB')
    offset=round(offset,1)
    changed=ep['data'].get('package') and ep['status'] in ('COMPLETE','FAILED','AWAITING_ASSETS','ASSETS_BLOCKED')
    return update_episode(eid,'AWAITING_ASSETS' if changed else ep['status'],music_mix=dict(offset_db=offset,recorded_at=now()),error=None,
                          message=f'Music level set to {offset:+.1f} dB relative to the automatic balance; the next render uses it')

@app.post('/api/episodes/{eid}/audio-preview')
def audio_preview(eid:int,payload:dict):
    """Build a short-lived listening mix (narration + ducked music at the given offset) in the isolated
    worker. Nothing is saved to the episode settings and no video render is queued."""
    import sys,uuid,time
    ep=episode(eid);approved(ep)
    if ep['status'] in ('QUEUED','RENDERING'):
        raise ValueError('A render is in progress; try the audio preview when it finishes')
    try:offset=float(payload.get('offset_db'))
    except (TypeError,ValueError):raise ValueError('Provide offset_db as a number')
    if not -12<=offset<=6:raise ValueError('Music level offset must be between -12 and +6 dB')
    directory=epdir(ep)
    jobid='audio-preview-'+uuid.uuid4().hex
    with episode_lock(directory,'media',blocking=False):
        result=isolation.launch(directory,[sys.executable,'-B',str(ROOT/'scripts/production_worker.py'),'audio-preview',str(eid),str(round(offset,1))],jobid,timeout=240)
    if result['returncode']:
        raise ValueError('Audio preview failed: '+(result['stderr'] or result['stdout'])[-1500:])
    out=directory/'06_edit/audio_preview/preview_mix.m4a'
    if not out.is_file():raise ValueError('Audio preview was not produced')
    info=json.loads((result['stdout'] or '{}').strip().splitlines()[-1])
    rel=out.relative_to(STORE).as_posix()
    return dict(url='/api/media/'+rel+'?v='+str(int(time.time())),offset_db=round(offset,1),gap_db=info.get('gap_db'),
                message=f'Preview ready at {offset:+.1f} dB. Nothing was saved and no video was rendered.')

def _style_busy(ep):
    if ep['status'] in ('QUEUED', 'RENDERING'):
        raise ValueError('A render is in progress; change the style after it finishes')


def _style_summary(ep):
    from . import styles
    directory = epdir(ep)
    effective = styles.effective_style(ep)
    pinned = styles.available_profiles(directory)
    shared = styles.profiles_doc(ROOT)
    shared_profiles = shared['profiles'] if shared else {}
    meta = lambda p: dict(id=p['id'], label=p['label'], version=p['version'], description=p.get('description', ''), transitions=p['transitions']['allowed'])
    preview_path = directory / '06_edit/style_preview/preview.json'
    return dict(profile_id=effective['profile_id'], label=effective['profile']['label'], version=effective['version'], source=effective['source'],
                pinned=[meta(p) for p in pinned.values()],
                adoptable=[meta(p) for k, p in shared_profiles.items() if k not in pinned],
                overrides=(ep['data'].get('style_overrides') or {}).get('transitions', {}),
                preview=read_json(preview_path) if preview_path.is_file() else None)


@app.get('/api/styles')
def global_styles():
    from . import styles
    doc = styles.profiles_doc(ROOT)
    return dict(default_profile=doc['default_profile'],
                profiles=[dict(id=p['id'], label=p['label'], version=p['version'], description=p.get('description', '')) for p in doc['profiles'].values()])


@app.put('/api/episodes/{eid}/style')
def set_style(eid: int, payload: dict):
    """Owner selects/adopts an editing profile for ONE episode. Never changes script, stills or narration."""
    from . import styles
    ep = episode(eid)
    _style_busy(ep)
    pid = payload.get('profile_id')
    directory = epdir(ep)
    pinned = styles.available_profiles(directory)
    current = ep['data'].get('style') or {}
    if pid in pinned:
        style = dict(profile_id=pid, version=pinned[pid]['version'], doc_sha256=current.get('doc_sha256'),
                     renderer_dir=current.get('renderer_dir', 'remotion'), source='owner_selected', pinned_at=now())
    else:
        shared = styles.profiles_doc(ROOT)
        if not shared or pid not in shared['profiles']:
            raise ValueError('Unknown editing profile')
        if payload.get('adopt') is not True:
            raise ValueError('This episode has not pinned that profile. Confirm adoption to add it (existing files are not changed).')
        style = styles.pin_style_upgrade(directory, pid)
    rerender = bool(payload.get('rerender')) and bool(ep['data'].get('package')) and ep['status'] in ('COMPLETE', 'FAILED', 'AWAITING_ASSETS', 'ASSETS_BLOCKED')
    label = (pinned.get(pid) or (styles.profiles_doc(ROOT) or {}).get('profiles', {}).get(pid, {})).get('label', pid)
    return update_episode(eid, 'AWAITING_ASSETS' if rerender else ep['status'], style=style, error=None,
                          message=f'Editing style set to {label}.' + (' Re-rendering as a new export version.' if rerender else ' The next render uses it; existing exports are untouched.'))


@app.put('/api/episodes/{eid}/transitions')
def set_transitions(eid: int, payload: dict):
    """Owner transition requests per scene boundary. Validated again (profile limits) at render time."""
    from . import styles
    ep = episode(eid)
    _style_busy(ep)
    if not ep['data'].get('package'):
        raise ValueError('Transitions can be edited after preproduction')
    ids = [s['scene_id'] for s in ep['data']['package']['scenes']]
    requested = payload.get('transitions')
    if not isinstance(requested, dict):
        raise ValueError('Provide transitions as {scene_id: ' + '|'.join(styles.ALL_TRANSITIONS) + '}')
    clean = {}
    for scene_id, name in requested.items():
        if scene_id not in ids or ids.index(scene_id) == 0:
            raise ValueError('Transitions apply to scenes S002 onward: ' + str(scene_id))
        if name not in styles.ALL_TRANSITIONS:
            raise ValueError('Unknown transition: ' + str(name))
        clean[scene_id] = name
    rerender = bool(payload.get('rerender')) and ep['status'] in ('COMPLETE', 'FAILED', 'AWAITING_ASSETS', 'ASSETS_BLOCKED')
    return update_episode(eid, 'AWAITING_ASSETS' if rerender else ep['status'], style_overrides=dict(transitions=clean, recorded_at=now()), error=None,
                          message='Scene transitions saved. The pinned style still enforces its limits.' + (' Re-rendering as a new export version.' if rerender else ''))


@app.post('/api/episodes/{eid}/style-preview')
def style_preview_endpoint(eid: int, payload: dict):
    """Render ~5-8 s per profile in the isolated worker. Never overwrites exports or episode settings."""
    import sys
    import uuid
    from . import styles
    ep = episode(eid)
    _style_busy(ep)
    wanted = payload.get('profiles') or [styles.CLASSIC_ID, styles.TRANSITIONS_ID]
    shared = (styles.profiles_doc(ROOT) or {}).get('profiles', {})
    allowed = set(styles.available_profiles(epdir(ep))) | set(shared)
    if not isinstance(wanted, list) or not wanted or len(wanted) > 3 or any(p not in allowed for p in wanted):
        raise ValueError('Choose one to three known editing profiles')
    directory = epdir(ep)
    jobid = 'style-preview-' + uuid.uuid4().hex
    with episode_lock(directory, 'media', blocking=False):
        result = isolation.launch(directory, [sys.executable, '-B', str(ROOT / 'scripts/production_worker.py'), 'style-preview', str(eid), ','.join(wanted)],
                                  jobid, network=True, timeout=900)
    if result['returncode']:
        raise ValueError('Style preview failed: ' + (result['stderr'] or result['stdout'])[-1500:])
    meta = read_json(directory / '06_edit/style_preview/preview.json')
    return dict(preview=meta, message='Style preview ready (' + str(meta['window_seconds']) + ' s). Your exports and episode settings were not changed.')


@app.put('/api/episodes/{eid}/caption-regions')
def caption_regions(eid:int,payload:list[dict]):
    from .models import Scene
    from .media import caption_position
    ep=episode(eid);approved(ep)
    if ep['status'] in ('QUEUED','RENDERING') or not ep['data'].get('package'):
        raise ValueError('Caption region edits require a prepared, idle episode')
    package=ep['data']['package']; scenes=package['scenes']
    if len(payload)!=len(scenes) or {r.get('scene_id') for r in payload}!={s['scene_id'] for s in scenes}:
        raise ValueError('Supply exactly one region record per existing scene')
    mapped={r['scene_id']:r for r in payload}
    updated=[]
    for scene in scenes:
        row=mapped[scene['scene_id']]
        if set(row)-{'scene_id','protected_regions','caption_y'}:
            raise ValueError('Only caption_y and protected_regions can be edited here')
        new=Scene.model_validate({**scene,**row}).model_dump()
        if any(r['x']+r['width']>1 or r['y']+r['height']>1 for r in new['protected_regions']):
            raise ValueError('Protected region exceeds image bounds')
        caption_position(new)
        updated.append(new)
    package={**package,'scenes':updated}
    write_json(epdir(ep)/'06_edit/caption_region_adjustments.json',dict(at=now(),regions=payload,approved_narration_unchanged=ep['data']['approval']['sha256']))
    return update_episode(eid,'AWAITING_ASSETS',package=package,error=None,message='Caption-safe regions updated; narration, scene IDs and illustrations unchanged')

@app.get('/api/episodes/{eid}/file/{relative:path}')
def episode_file(eid:int,relative:str):
    if any(p.lower()=='.production' for p in Path(relative).parts):raise HTTPException(404)
    root=epdir(episode(eid));candidate=EpisodeWriter(root).path(relative);no_links(candidate);path=candidate.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path,filename=path.name)

@app.get('/api/media/{relative:path}')
def media_file(relative:str):
    parts=Path(relative).parts
    if Path(relative).is_absolute() or len(parts)<3 or parts[0].lower()!='episodes' or '..' in parts or any(p.rstrip(' .').lower()=='.production' for p in parts):raise HTTPException(404)
    root=(STORE/'episodes').resolve()
    path=EpisodeWriter(root/parts[1]).path('/'.join(parts[2:])).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)

@app.get('/api/providers')
def provider_inventory():
    return dict(providers=providers.inventory(),isolation=isolation.status(),selected=settings()['provider'])

@app.get('/api/controller/status')
def controller_status(request:Request):
    """Lets the dashboard tell the owner whether THIS browser is authorised to make changes (never reveals the key)."""
    import secrets
    supplied=request.headers.get('x-odd-controller','')
    return dict(authorized=bool(supplied) and secrets.compare_digest(supplied,controller_token()))

@app.get('/api/providers/credentials')
def provider_credentials():
    return dict(credentials=providers.credential_status())

@app.put('/api/providers/credentials/{name}')
def provider_credential_set(name:str,payload:dict):
    if set(payload)-{'value'}:raise ValueError('Send only the token value')
    return dict(credentials=providers.set_credential(name,payload.get('value','')))

@app.delete('/api/providers/credentials/{name}')
def provider_credential_clear(name:str):
    return dict(credentials=providers.clear_credential(name))

@app.post('/api/providers/{provider}/test')
def provider_test(provider:str):
    if provider not in providers.PROVIDERS:raise ValueError('Unknown AI provider')
    return providers.test_connection(provider)

@app.post('/api/episodes/{eid}/isolation/verify')
def verify_episode_isolation(eid:int):
    return isolation.verify_boundary(epdir(episode(eid)))

@app.post('/api/runs/{runid}/cancel')
def cancel_generation(runid:str):return cancel_run(runid)

@app.post('/api/runs/{runid}/retry')
def retry_generation(runid:str):
    with db() as c:row=c.execute('SELECT * FROM runs WHERE id=?',(runid,)).fetchone()
    if not row or row['status'] not in ('FAILED','CANCELLED'):raise ValueError('Only failed or cancelled runs can be retried')
    if row['task']=='genre_ideas':
        from .story_ideas import retry_run
        return retry_run(runid)
    payload=json.loads(json.loads(row['request'])['messages'][1]['content'])
    result=start_task(row['task'],payload,row['episode_id'],background=True)
    from .creative import run_event
    run_event(result['run_id'],'job.retry','Explicit retry created a new request; previous records are preserved',retry_of=runid)
    return result

@app.get('/api/metrics')
def metrics():
    with db() as c:
        return [dict(id=r['id'],episode_id=r['episode_id'],created=r['created'],**json.loads(r['payload'])) for r in c.execute('SELECT * FROM metrics ORDER BY id DESC')]

@app.post('/api/episodes/{eid}/metrics')
def save_metrics(eid:int,payload:dict):
    episode(eid)
    if not payload.get('period') or not payload.get('source'):
        raise ValueError('Record the metric reporting period and real source')
    for key in ['views','reach','shares','comments','follows','average_watch_seconds']:
        if key in payload and payload[key] is not None and (not isinstance(payload[key],(int,float)) or payload[key]<0):
            raise ValueError('Metrics must be actual nonnegative numbers or null')
    with db() as c:
        c.execute('INSERT INTO metrics(episode_id,payload,created) VALUES (?,?,?)',(eid,json.dumps(payload),now()))
    return dict(saved=True)

dist=ROOT/'apps/dashboard/dist'
if dist.exists():
    class DashboardFiles(StaticFiles):
        async def get_response(self,path,scope):
            try:return await super().get_response(path,scope)
            except StarletteHTTPException as exc:
                if exc.status_code==404 and not path.startswith('api/') and '.' not in Path(path).name:
                    return await super().get_response('index.html',scope)
                raise
    app.mount('/',DashboardFiles(directory=dist,html=True),name='dashboard')
