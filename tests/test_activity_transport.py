import asyncio
import json
from types import SimpleNamespace
from services.api import activity,main,core,creative
from .fixtures import IDEA

def test_sse_replays_only_unseen_events_and_keeps_episode_scope(store):
    ep=creative.create_episode(IDEA);root=core.epdir(ep)
    events=[activity.emit(root,'test-job',ep['id'],'codex_cli','prepare','ai.activity',str(i)) for i in range(3)]
    cursor=activity.encode_cursor({'test-job':1})
    # Exercise the actual StreamingResponse generator without a never-ending TestClient read.
    class Request:
        headers={'last-event-id':cursor}
        query_params={}
        async def is_disconnected(self):return False
    async def read():
        original=activity.collect
        activity.collect=lambda eid:[dict(job_id='test-job',events=events)] if eid==ep['id'] else []
        try:
            response=await main.activity_stream(Request(),ep['id']);iterator=response.body_iterator
            parts=[await anext(iterator) for _ in range(3)]
            await iterator.aclose()
            return parts
        finally:activity.collect=original
    parts=asyncio.run(read())
    assert parts[0].startswith('retry:')
    assert 'test-job:2' in parts[1] and 'test-job:3' in parts[2]
    assert 'test-job:1' not in ''.join(parts)

def test_activity_filters_multiple_episodes_and_retry_records(store):
    a=creative.create_episode(IDEA);b=creative.create_episode(IDEA)
    one=creative.start_task('script',dict(idea=IDEA),a['id'])
    two=creative.start_task('script',dict(idea=IDEA),b['id'])
    all_jobs=activity.collect()
    assert {j['episode_id'] for j in all_jobs}=={a['id'],b['id']}
    filtered=activity.collect(a['id'])
    assert len(filtered)==1 and filtered[0]['job_id']==one['run_id']
    assert filtered[0]['status']=='AWAITING_MANUAL' and not filtered[0]['cancellable']

def test_cancelled_background_generation_is_persisted_without_real_cli(store,monkeypatch):
    import threading,time
    from services.api import providers
    monkeypatch.setenv('ODD_AI_PROVIDER','codex_cli')
    entered=threading.Event()
    def fake_generate(config,messages,schema,root,runid,cancel):
        entered.set();cancel.wait(4)
        raise providers.ProviderError('Generation cancelled','CANCELLED')
    monkeypatch.setattr(providers,'generate',fake_generate)
    started=creative.start_task('ideas',{},background=True)
    assert entered.wait(5)
    creative.cancel_run(started['run_id'])
    for _ in range(80):
        with core.db() as c:status=c.execute('SELECT status FROM runs WHERE id=?',(started['run_id'],)).fetchone()[0]
        jobs=activity.collect()
        if status=='CANCELLED' and any(e['type']=='job.cancelled' for e in jobs[0]['events']):break
        time.sleep(.05)
    assert status=='CANCELLED'
    jobs=activity.collect()
    assert any(e['type']=='job.cancelled' for e in jobs[0]['events'])
