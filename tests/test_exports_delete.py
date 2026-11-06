"""Multi-delete of finished exports. No model usage, no rendering: synthetic files inside a disposable store."""
import pytest
from services.api import core, main
from .test_station import prepared


def episode_with_exports(count=4):
    ep = prepared()
    root = core.epdir(ep)
    (root / '07_export/final').mkdir(parents=True, exist_ok=True)
    (root / '06_edit/previews').mkdir(parents=True, exist_ok=True)
    entries = []
    for jid in range(1, count + 1):
        final = root / f'07_export/final/{ep["code"]}_v{jid:03d}.mp4'
        final.write_bytes(b'mp4-' + bytes([jid]))
        preview = root / f'06_edit/previews/preview_{jid}.mp4'
        preview.write_bytes(b'pv')
        rel = lambda p: f'episodes/{root.name}/' + p.relative_to(root).as_posix()
        entries.append(dict(path=rel(final), preview=rel(preview), job_id=jid, created=core.now(), qc='PASS'))
    core.update_episode(ep['id'], 'COMPLETE', exports=entries)
    return core.episode(ep['id']), root


def test_deletes_only_the_selected_exports_and_their_previews(store):
    ep, root = episode_with_exports()
    (root / '05_assets').mkdir(exist_ok=True)
    keep_asset = root / '05_assets/keep.txt'
    keep_asset.write_text('x')
    out = main.delete_exports(ep['id'], dict(job_ids=[1, 3], confirm=True))
    assert out['deleted'] == [1, 3] and out['remaining'] == 2
    names = sorted(p.name for p in (root / '07_export/final').glob('*.mp4'))
    assert names == [f'{ep["code"]}_v002.mp4', f'{ep["code"]}_v004.mp4']
    assert not (root / '06_edit/previews/preview_1.mp4').exists() and (root / '06_edit/previews/preview_2.mp4').exists()
    after = core.episode(ep['id'])
    assert [e['job_id'] for e in after['data']['exports']] == [2, 4] and after['status'] == 'COMPLETE'
    assert after['data']['export_deletions'][-1]['job_ids'] == [1, 3] and keep_asset.exists()


def test_requires_confirmation_known_ids_and_idle_episode(store):
    ep, root = episode_with_exports(2)
    for payload, message in ((dict(job_ids=[1]), 'Confirm'), (dict(job_ids=[], confirm=True), 'Choose'), (dict(job_ids=[True], confirm=True), 'Choose'),
                             (dict(job_ids=['1'], confirm=True), 'Choose'), (dict(job_ids=[99], confirm=True), 'Unknown export')):
        with pytest.raises(ValueError, match=message):
            main.delete_exports(ep['id'], payload)
    assert len(list((root / '07_export/final').glob('*.mp4'))) == 2
    core.update_episode(ep['id'], 'RENDERING')
    with pytest.raises(ValueError, match='render is in progress'):
        main.delete_exports(ep['id'], dict(job_ids=[1], confirm=True))
    assert len(list((root / '07_export/final').glob('*.mp4'))) == 2


def test_refuses_recorded_paths_outside_the_export_folder(store):
    ep, root = episode_with_exports(2)
    victim = root / '05_assets/narration.wav'
    victim.parent.mkdir(exist_ok=True)
    victim.write_bytes(b'precious')
    entries = core.episode(ep['id'])['data']['exports']
    entries[0]['path'] = f'episodes/{root.name}/05_assets/narration.wav'
    core.update_episode(ep['id'], exports=entries)
    with pytest.raises(ValueError, match='outside the export folder'):
        main.delete_exports(ep['id'], dict(job_ids=[1], confirm=True))
    entries[0]['path'] = f'episodes/{root.name}/../escape.mp4'
    core.update_episode(ep['id'], exports=entries)
    with pytest.raises(ValueError, match='outside this episode'):
        main.delete_exports(ep['id'], dict(job_ids=[1], confirm=True))
    assert victim.read_bytes() == b'precious'


def test_missing_files_are_tolerated_and_the_record_is_still_removed(store):
    ep, root = episode_with_exports(2)
    (root / f'07_export/final/{ep["code"]}_v001.mp4').unlink()
    out = main.delete_exports(ep['id'], dict(job_ids=[1], confirm=True))
    assert out['deleted'] == [1] and [e['job_id'] for e in core.episode(ep['id'])['data']['exports']] == [2]
