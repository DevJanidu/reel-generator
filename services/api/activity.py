"""Bounded, episode-local public job journals. Never store provider text or reasoning."""
import base64
import json
from pathlib import Path
from .core import now, read_json
from .file_writer import EpisodeWriter, episode_lock

LIMIT = 600

def emit(root, job_id, episode_id, provider, stage, event_type, message, **details):
    writer = EpisodeWriter(root)
    # Job identifiers are controller-assigned, never model paths.
    if not str(job_id).replace('-', '').replace('_', '').isalnum():
        raise ValueError('Invalid activity job ID')
    relative = f'.production/activity/{job_id}.json'
    with episode_lock(root, 'activity'):
        path = writer.path(relative)
        journal = read_json(path) if path.exists() else dict(sequence=0, events=[])
        seq = journal['sequence'] + 1
        event = dict(event_id=f'{job_id}:{seq}', sequence=seq, job_id=str(job_id), episode_id=episode_id,
                     attempt_id=str(job_id),
                     provider=provider, stage=stage, type=event_type, timestamp=now(), message=message)
        event['status']={'job.queued':'QUEUED','job.completed':'SUCCEEDED','ai.failed':'FAILED','job.cancelled':'CANCELLED'}.get(event_type,'RUNNING')
        for key in ('completed', 'total', 'file', 'status', 'retry_of'):
            if key in details: event[key] = details[key]
        journal.update(sequence=seq, events=(journal['events'] + [event])[-LIMIT:])
        if event_type == 'job.started': journal['started_at'] = event['timestamp']
        if event_type in ('job.completed', 'ai.failed', 'job.cancelled'): journal['finished_at'] = event['timestamp']
        writer.json(relative, journal)
    return event

def collect(episode_id=None):
    """Only the trusted controller reads the global index. Workers call emit only."""
    from .core import db, episode, epdir
    with db() as c:
        where=' WHERE episode_id=?' if episode_id is not None else ''
        params=(episode_id,) if episode_id is not None else ()
        priority=" ORDER BY CASE WHEN status IN ('QUEUED','RUNNING') THEN 0 ELSE 1 END, created DESC LIMIT 100"
        runs = [dict(r) for r in c.execute('SELECT * FROM runs'+where+priority,params)]
        renders = [dict(r) for r in c.execute('SELECT * FROM jobs'+where+priority,params)]
    jobs = []
    for row in runs + renders:
        if episode_id is not None and row['episode_id'] != episode_id: continue
        is_ai = 'workspace' in row
        jid = str(row['id']) if is_ai else 'render-' + str(row['id'])
        # One job whose workspace is gone (manual/idea runs have none; deleted episodes) must never break the whole feed.
        try:
            root = Path(row['workspace']) if is_ai and row.get('workspace') else epdir(episode(row['episode_id']))
            writer = EpisodeWriter(root)
            path = writer.path(f'.production/activity/{jid}.json')
            journal = read_json(path) if path.exists() else dict(sequence=0, events=[])
            if not is_ai and row['status'] in ('QUEUED','RUNNING'):
                local=writer.path(f'.production/jobs/{row["id"]}.json')
                if local.exists():
                    state=read_json(local)
                    row['stage']=state.get('stage',row.get('stage'))
        except (OSError, ValueError, KeyError, TypeError):
            journal = dict(sequence=0, events=[])
        if row['status']=='RUNNING' and journal['events']:
            row['stage']=journal['events'][-1]['message']
        from .providers import classify
        error_code=classify(row['error']) if row.get('error') else None
        diagnosis={'AUTHENTICATION':'Refresh login or configure the authorized credential in Settings, then retry.',
                   'USAGE_LIMIT':'Provider usage limit reached. Wait for quota recovery before retrying.',
                   'TIMEOUT':'The provider timed out. Check connection and timeout settings, then retry.',
                   'ISOLATION_UNAVAILABLE':'Native isolation is unavailable. Automatic execution remains disabled; check the episode isolation report.',
                   'INVALID_OUTPUT':'The provider response failed validation. Retry without changing the approved script.'}
        # No raw provider exception (paths, model output or credentials) is public here.
        jobs.append(dict(job_id=jid, episode_id=row['episode_id'], provider=row.get('provider') or 'remotion',
                         task=row.get('task') or row.get('kind'), status=row['status'], stage=row.get('stage'),
                         created=row['created'], started_at=journal.get('started_at'), finished_at=journal.get('finished_at'),
                         error=diagnosis.get(error_code,'Operation failed. Check provider status and the episode asset report before retrying.') if error_code else None,
                         events=journal['events'], sequence=journal['sequence'],
                         cancellable=is_ai and row.get('task')!='connection_test' and (row['status'] in ('QUEUED','RUNNING') or (row.get('task')=='genre_ideas' and row['status']=='AWAITING_MANUAL')),
                         retryable=is_ai and row.get('task')!='connection_test' and row['status'] in ('FAILED','CANCELLED')))
        if is_ai:
            view=run_view(row)
            jobs[-1].update({k:view[k] for k in ('generation_progress','attempt_number','job_group_id','retry_of','failure','error','worker_timeout_seconds')})
            jobs[-1]['stage']=view['stage']
            if row['episode_id']:
                try:
                    ep=episode(row['episode_id']);jobs[-1].update(episode_code=ep['code'],episode_title=ep['title'])
                except (ValueError,KeyError):pass
    return jobs

def run_view(row):
    """One safe attempt projection used by episode, queue, runs and activity APIs."""
    row=dict(row);provenance=json.loads(row.get('provenance') or '{}')
    public={k:row.get(k) for k in ('id','episode_id','task','status','created','stage','progress','provider')}
    public.update(attempt_number=provenance.get('attempt_number',1),job_group_id=provenance.get('job_group_id',row['id']),retry_of=provenance.get('retry_of'),failure=None,error=None,generation_progress=None)
    public['events']=[]
    public['worker_timeout_seconds']=provenance.get('timeout_seconds')
    root=row.get('workspace')
    if root and Path(root).is_dir():
        writer=EpisodeWriter(root)
        journal=writer.path(f'.production/activity/{row["id"]}.json')
        if journal.exists():public['events']=read_json(journal).get('events',[])[-40:]
        public['generation_progress']=generation_progress(root,row['id'],row['status'],row.get('stage'),row.get('provider'),row.get('task'))
        if row['status']=='RUNNING':public['stage']=public['generation_progress']['message']
        path=writer.path(f'.production/runs/{row["id"]}/failure.json')
        if row['status'] in ('FAILED','CANCELLED') and path.exists():public['failure']=read_json(path)['public']
    if row.get('error') and row['status'] in ('FAILED','CANCELLED'):
        from .job_errors import diagnosis
        public['failure']=public['failure'] or {**diagnosis(row['error']),'failed_stage':row.get('stage'),'failed_at':None}
        public['error']=public['failure']['category']+': '+public['failure']['message']
    return public

def encode_cursor(cursor):
    return base64.urlsafe_b64encode(json.dumps(cursor, separators=(',', ':')).encode()).decode()

def decode_cursor(value):
    try:
        data = json.loads(base64.urlsafe_b64decode(value))
        return {str(k): int(v) for k,v in data.items()} if len(data) <= 200 else {}
    except (ValueError, TypeError, AttributeError): return {}

def provider_activity(provider, event):
    """Allowlisted metadata only. Never forward text, deltas, tool arguments or thinking."""
    kind = event.get('type')
    if provider == 'codex_cli':
        if kind == 'thread.started': return 'Provider session established'
        if kind == 'turn.started': return 'Provider is generating the structured response'
        if kind == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
            return 'Provider response received; schema validation is pending'
        if kind == 'turn.completed': return 'Provider turn ended; output checks are pending'
    elif provider == 'claude_cli':
        if kind == 'system' and event.get('subtype') == 'init': return 'Provider session established'
        if kind == 'assistant': return 'Provider response activity received; validation is pending'
        if kind == 'result': return 'Provider turn ended; output checks are pending'
    return None


def generation_progress(root, job_id, status, fallback, provider, task='genre_ideas'):
    """Read only public milestones, scoped to this run. Never infer remote acceptance from RUNNING."""
    label={'codex_cli':'Codex CLI','claude_cli':'Claude Code CLI','openai-compatible':'AI API'}.get(provider,'Provider')
    phase='queued' if status in ('QUEUED','PREPARING') else 'preflight'
    message=fallback or 'Waiting for provider checks'
    milestones=[];last_event_at=None;sent=False;last_process_check=None;last_provider_event=None
    path=EpisodeWriter(root).path(f'.production/activity/{job_id}.json')
    journal=read_json(path) if path.exists() else {'events':[]}
    mapped={
        'provider.checking':('preflight','Checking provider authentication'),
        'provider.authenticated':('preflight','Provider authentication check passed'),
        'isolation.checking':('preflight','Checking native isolation'),
        'isolation.verified':('preflight','Native isolation verified; preparing CLI launch'),
        'ai.started':('launching',f'{label} process started; sending the request'),
        'request.sent':('sent',f'Request sent to {label}; waiting for provider activity'),
        'output.repair':('validating','Checking concepts; preparing one validation retry'),
        'output.validating':('validating','Response received; validating the stage contract'),
        'output.saving':('saving','Validated output received; saving production artifacts'),
        'output.parsing':('validating','Parsing the complete provider JSON response'),
        'output.parsed':('validating','Provider JSON parsed; controller schema validation is pending'),
        'ai.completed':('validating','Provider response received; validation is pending'),
    }
    legacy={
        'Provider session established':('connected',f'{label} session established'),
        'Provider is generating the structured response':('generating',f'{label} is generating the structured response'),
        'Provider response activity received; validation is pending':('generating',f'{label} response activity received'),
        'Provider response received; schema validation is pending':('validating','Response received; schema validation is pending'),
        'Provider turn ended; output checks are pending':('validating','Provider turn ended; checking output'),
    }
    for event in journal.get('events',[]):
        if event.get('type')=='process.alive':last_process_check=event['timestamp']
        if event.get('type') in ('ai.started','ai.completed','request.sent') or (event.get('type')=='ai.activity' and event.get('message') in legacy):last_provider_event=event['timestamp']
        item=mapped.get(event.get('type')) or (legacy.get(event.get('message')) if event.get('type')=='ai.activity' else None)
        if item:
            phase,message=item;last_event_at=event['timestamp']
            if phase in ('sent','connected','generating'):sent=True
            milestones.append(dict(phase=phase,message=message,timestamp=last_event_at))
    if status=='AWAITING_MANUAL':phase,message='manual','Manual handoff ready; no automatic provider call'
    elif status=='SUCCEEDED':phase,message='complete',{'genre_ideas':'Five concepts validated and ready','prepare':'Production package validated and saved','script':'Script generated; internal review is next','review':'Reviewed script ready for owner approval'}.get(task,'Provider stage completed and validated')
    elif status in ('FAILED','CANCELLED'):phase,message=status.lower(),'Generation failed' if status=='FAILED' else 'Generation cancelled'
    return dict(phase=phase,message=message,request_sent=sent,last_event_at=last_event_at,last_provider_event_at=last_provider_event,last_process_check_at=last_process_check,milestones=milestones[-8:])
