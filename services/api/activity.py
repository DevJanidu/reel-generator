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
                     provider=provider, stage=stage, type=event_type, timestamp=now(), message=message)
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
        runs = [dict(r) for r in c.execute('SELECT id,episode_id,task,status,provider,stage,created,error,workspace FROM runs'+where+priority,params)]
        renders = [dict(r) for r in c.execute('SELECT * FROM jobs'+where+priority,params)]
    jobs = []
    for row in runs + renders:
        if episode_id is not None and row['episode_id'] != episode_id: continue
        is_ai = 'workspace' in row
        root = Path(row['workspace']) if is_ai and row.get('workspace') else epdir(episode(row['episode_id']))
        jid = str(row['id']) if is_ai else 'render-' + str(row['id'])
        path = EpisodeWriter(root).path(f'.production/activity/{jid}.json')
        journal = read_json(path) if path.exists() else dict(sequence=0, events=[])
        if not is_ai and row['status'] in ('QUEUED','RUNNING'):
            local=EpisodeWriter(root).path(f'.production/jobs/{row["id"]}.json')
            if local.exists():
                state=read_json(local)
                row['stage']=state.get('stage',row.get('stage'))
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
                         cancellable=is_ai and row.get('task')!='connection_test' and row['status'] in ('QUEUED','RUNNING'),
                         retryable=is_ai and row.get('task')!='connection_test' and row['status'] in ('FAILED','CANCELLED')))
    return jobs

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
