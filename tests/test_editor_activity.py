"""No model usage. Real media decoding for draft tests; native isolation has separate opt-in checks."""
import copy
import json
import pytest
from services.api import core, creative, editor, activity, worker
from .test_station import prepared,asset_fixture

def test_activity_sequences_are_episode_local_bounded_and_replayable(store,monkeypatch):
    ep=prepared();root=core.epdir(ep);other=prepared()
    monkeypatch.setattr(activity,'LIMIT',4)
    for i in range(7):activity.emit(root,'demo-job',ep['id'],'codex_cli','prepare','ai.activity',f'Milestone {i}')
    journal=core.read_json(root/'.production/activity/demo-job.json')
    assert [x['sequence'] for x in journal['events']]==[4,5,6,7]
    assert not (core.epdir(other)/'.production/activity/demo-job.json').exists()
    cursor={'demo-job':5,'other-job':9}
    assert activity.decode_cursor(activity.encode_cursor(cursor))==cursor
    assert activity.decode_cursor('malformed')=={}

@pytest.mark.parametrize('provider,event',[
    ('codex_cli',{'type':'item.completed','item':{'type':'reasoning','text':'PRIVATE'}}),
    ('claude_cli',{'type':'stream_event','event':{'delta':{'thinking':'PRIVATE'}}}),
])
def test_reasoning_never_becomes_public_activity(provider,event):
    assert activity.provider_activity(provider,event) is None
    assert 'PRIVATE' not in str(activity.provider_activity('codex_cli',{'type':'item.completed','item':{'type':'agent_message','text':'PRIVATE'}}))

def make_draft(store,monkeypatch):
    monkeypatch.setattr(editor,'STORE',store)
    from services.api import studio;monkeypatch.setattr(studio,'STORE',store)
    ep=prepared();root=asset_fixture(ep);jid=worker.enqueue(ep['id'])
    monkeypatch.setenv('ODD_EPISODE_WORKER','1');monkeypatch.setenv('EPISODE_WRITE_ROOT',str(root))
    editor.prepare(ep['id'],jid)
    monkeypatch.delenv('ODD_EPISODE_WORKER');monkeypatch.delenv('EPISODE_WRITE_ROOT')
    with core.db() as c:c.execute("UPDATE jobs SET status='COMPLETE' WHERE id=?",(jid,))
    return ep,root

def patch_for(draft):
    t=draft['timeline']
    return dict(revision=draft['state']['revision'],captions=[{k:v for k,v in c.items() if k in editor.CaptionEdit.model_fields} for c in t['captions']],
                scenes=[{k:s[k] for k in ('id','transition','transition_frames')} for s in t['scenes']],audio={k:v for k,v in t['audio'].items() if k!='envelope'})

def test_draft_is_complete_without_mp4_save_restores_and_conflicts(store,monkeypatch):
    ep,root=make_draft(store,monkeypatch)
    draft=editor.load(ep['id']);assert len(draft['timeline']['scenes'])==3
    assert draft['waveforms']['narration'] and draft['waveforms']['music']
    assert draft['timeline']['audioSources']==['narration','instrumental']
    assert core.episode(ep['id'])['status']=='EDIT_READY'
    assert not list(root.rglob('*.mp4'))
    patch=patch_for(draft);patch['audio']['music_gain']=.4
    editor.save(ep['id'],patch)
    assert editor.load(ep['id'])['timeline']['audio']['music_gain']==.4
    with pytest.raises(ValueError,match='Revision conflict'):editor.save(ep['id'],patch)
    assert core.read_json(root/'06_edit/revisions/000001.json')['audio']['music_gain']==1
    assert not list(root.rglob('*.mp4'))
    # Mutable compatibility mirrors cannot override the committed revision pointer.
    core.write_json(root/'06_edit/timeline.json',{'malformed':'interrupted mirror'})
    assert editor.load(ep['id'])['timeline']['audio']['music_gain']==.4

def test_editor_rejects_story_paths_motion_and_stale_assets(store,monkeypatch):
    ep,root=make_draft(store,monkeypatch);draft=editor.load(ep['id']);patch=patch_for(draft)
    patch['captions'][0]['text']='A rewritten story'
    with pytest.raises(ValueError,match='approved narration'):editor.save(ep['id'],patch)
    patch=patch_for(draft);patch['scenes'][0]['image']='../other.png'
    with pytest.raises(ValueError):editor.save(ep['id'],patch)
    patch=patch_for(draft);patch['scenes'][0]['transition']='crossfade'
    with pytest.raises(ValueError,match='first scene'):editor.save(ep['id'],patch)
    patch=patch_for(draft);patch['audio']['music_gain']=float('nan')
    with pytest.raises(ValueError):editor.save(ep['id'],patch)
    patch=patch_for(draft)
    (root/'05_assets/images/S001.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match='asset changed'):editor.save(ep['id'],patch)

def test_runtime_changes_fail_closed_without_repin(store,monkeypatch):
    ep,root=make_draft(store,monkeypatch)
    original=(root/'.production/provenance.json').read_bytes()
    (root/'06_edit/remotion/editor-v1/src/composition.tsx').write_text('changed')
    with pytest.raises(ValueError,match='integrity'):editor.load(ep['id'])
    assert (root/'.production/provenance.json').read_bytes()==original

def test_explicit_rebuild_preserves_prior_plan_revision_and_audio(store,monkeypatch):
    from services.api import main
    ep,root=make_draft(store,monkeypatch);old=editor.load(ep['id']);audio=root/old['timeline']['narration'].split(ep['path']+'/')[1]
    old_revision=(root/'06_edit/revisions/000001.json').read_bytes()
    queued=main.rebuild_editor(ep['id']);assert queued['job_id']
    assert (root/'06_edit/revisions/plan-000001.json').is_file()
    assert (root/'06_edit/revisions/000001.json').read_bytes()==old_revision and audio.is_file()
    with pytest.raises(ValueError,match='rebuild'):editor.load(ep['id'])
    with core.db() as c:c.execute("UPDATE jobs SET status='FAILED' WHERE id=?",(queued['job_id'],))
    core.update_episode(ep['id'],'FAILED')
    assert editor.needs_rebuild(ep['id'],{'fingerprints':{}})
    with pytest.raises(ValueError,match='rebuild'):editor.save(ep['id'],patch_for(old))

def test_export_retry_uses_the_saved_timeline_instead_of_replacing_draft(store,monkeypatch):
    from services.api import main
    ep,root=make_draft(store,monkeypatch)
    core.update_episode(ep['id'],'FAILED')
    before=(root/'06_edit/revisions/000001.json').read_bytes()
    monkeypatch.setattr(main,'secure_validate',lambda eid:dict(valid=True,fingerprints=core.read_json(root/'06_edit/edit_plan.json')['asset_fingerprints']))
    queued=main.retry(ep['id'])
    with core.db() as c:job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(queued['job_id'],)).fetchone())
    assert job['kind']=='render'
    assert (root/'06_edit/revisions/000001.json').read_bytes()==before


def test_activity_feed_survives_jobs_without_a_resolvable_workspace(store):
    from services.api import core, activity
    with core.db() as c:
        c.execute("INSERT INTO runs(id,episode_id,task,status,request,provenance,created,workspace,stage,progress,provider) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  ('orphan-run', None, 'ideas', 'AWAITING_MANUAL', '{}', '{}', core.now(), None, 'Waiting', 0, 'manual'))
        c.execute("INSERT INTO runs(id,episode_id,task,status,request,provenance,created,workspace,stage,progress,provider) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  ('ghost-run', 999, 'prepare', 'FAILED', '{}', '{}', core.now(), '', 'Failed', 0, 'codex_cli'))
    jobs = activity.collect()
    assert {'orphan-run', 'ghost-run'} <= {j['job_id'] for j in jobs}
