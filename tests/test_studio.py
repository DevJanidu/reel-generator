"""Official Remotion Studio integration. No model usage; one test starts the real Studio CLI on a free loopback port."""
import re
import urllib.request
import pytest
from services.api import core, studio, main
from .fixtures import IDEA
from .test_editor_activity import make_draft


def test_prepare_builds_a_complete_source_authored_studio_project(store, monkeypatch):
    ep, root = make_draft(store, monkeypatch)
    base = studio.studio_dir(root)
    m = studio.manifest(root)
    assert m and m['composition_id'] == 'OF-R001' and m['width'] == 1080 and m['height'] == 1920 and m['fps'] == 30
    for rel in ('src/index.ts', 'src/Root.tsx', 'src/Episode.tsx', 'src/lib/library.tsx', 'src/lib/composition.tsx', 'remotion.config.ts',
                'public/audio/narration.wav', 'public/audio/instrumental.wav', 'public/images/S001.png', 'public/fonts/barlow-condensed-800.woff2'):
        assert (base / rel).is_file(), rel
    source = (base / 'src/Episode.tsx').read_text(encoding='utf-8')
    names = re.findall(r'name=\{"([^"]+)"\}', source)
    assert len([n for n in names if re.match(r'S\d{3}', n)]) == 3
    assert sum(n.startswith('CAP') for n in names) == len(core.read_json(root / '06_edit/captions.json'))
    assert 'NARRATION — ElevenLabs' in names and 'MUSIC — Signature Instrumental' in names
    assert '<Audio' not in source and 'interpolate' not in source
    check = studio.check_source(root)
    assert check['errors'] == [] and len(check['scenes']) == 3 and studio.validate_project(root)
    assert studio.owner_changes(root) == []
    # Everything the Studio can serve or edit lives inside this episode; nothing global is written.
    assert all(p.resolve().is_relative_to(root.resolve()) for p in base.rglob('*'))


def test_owner_studio_edits_are_detected_kept_and_archived_before_replacement(store, monkeypatch):
    ep, root = make_draft(store, monkeypatch)
    base = studio.studio_dir(root)
    root_tsx = base / 'src/Root.tsx'
    original = root_tsx.read_text(encoding='utf-8')
    edited = original.replace('music_gain: 1', 'music_gain: 0.7')
    assert edited != original
    root_tsx.write_text(edited, encoding='utf-8')            # what Studio's "save default props" does
    assert studio.owner_changes(root) == ['src/Root.tsx']
    props = core.read_json(root / '06_edit/revisions/000001.json')
    scenes = core.episode(ep['id'])['data']['package']['scenes']
    with pytest.raises(ValueError, match='has your edits'):
        studio.generate(root, props, scenes, ep['code'])
    assert root_tsx.read_text(encoding='utf-8') == edited     # untouched
    studio.generate(root, props, scenes, ep['code'], force=True)
    archived = list((base / 'revisions').glob('*-before-regenerate/src/Root.tsx'))
    assert archived and 'music_gain: 0.7' in archived[-1].read_text(encoding='utf-8')   # recoverable revision
    assert studio.owner_changes(root) == []


def _drop_audio(s):
    return s.replace('</StudioStage>', "<Audio src={staticFile('x.wav')} /></StudioStage>")


def _move(s):
    return s.replace('<StaticStoryScene src=', '<StaticStoryScene style={{transform: "scale(1.2)"}} src=', 1)


def _gap(s):
    # Lengthening one still inside the TransitionSeries pushes the story past the narration.
    return re.sub(r'(name=\{"S003[^"]*"\}\s*durationInFrames=\{)(\d+)', lambda m: m.group(1) + str(int(m.group(2)) + 400), s, count=1)


def _twin(s):
    return s.replace('</StudioStage>', '<Sequence name={"NARRATION — second"} from={0} durationInFrames={10} /></StudioStage>')


@pytest.mark.parametrize('mutate,expected', [(_drop_audio, 'Audio/video'), (_move, 'Image movement'), (_gap, 'The stills run to frame'), (_twin, 'Exactly one narration')])
def test_source_policy_blocks_movement_sfx_gaps_and_duplicate_sources(store, monkeypatch, mutate, expected):
    ep, root = make_draft(store, monkeypatch)
    path = studio.studio_dir(root) / 'src/Episode.tsx'
    path.write_text(mutate(path.read_text(encoding='utf-8')), encoding='utf-8')
    assert expected in ' '.join(studio.check_source(root)['errors'])
    with pytest.raises(ValueError):
        main.studio_render(ep['id'])                          # export is refused, not silently "fixed"


def test_text_that_mentions_zoom_or_scale_is_not_mistaken_for_motion(store, monkeypatch):
    ep, root = make_draft(store, monkeypatch)
    path = studio.studio_dir(root) / 'src/Episode.tsx'
    path.write_text(path.read_text(encoding='utf-8').replace('text={"', 'text={"I scale the wall, zoom in and rotate ', 1), encoding='utf-8')
    assert studio.check_source(root)['errors'] == []


def test_two_episodes_have_independent_studio_projects(store, monkeypatch):
    a, root_a = make_draft(store, monkeypatch)
    b, root_b = make_draft(store, monkeypatch)
    assert studio.studio_dir(root_a) != studio.studio_dir(root_b)
    path = studio.studio_dir(root_a) / 'src/Root.tsx'
    path.write_text(path.read_text(encoding='utf-8') + '\n// edited\n', encoding='utf-8')
    assert studio.owner_changes(root_a) == ['src/Root.tsx'] and studio.owner_changes(root_b) == []


def test_status_summary_and_open_guard(store, monkeypatch):
    ep, root = make_draft(store, monkeypatch)
    info = main._studio_summary(core.episode(ep['id']))
    assert info['exists'] and info['valid'] and info['composition_id'] == 'OF-R001' and info['scene_sequences'] == 3
    assert info['session'] == dict(running=False) and 'visual' in info['capabilities']
    fresh = main.select(IDEA)
    assert main._studio_summary(core.episode(fresh['id']))['exists'] is False


def test_real_official_studio_starts_on_a_free_loopback_port_and_reports_real_readiness(store, monkeypatch):
    ep, root = make_draft(store, monkeypatch)
    state = dict(status='STARTING', events=[])
    result = studio._start(ep['id'], root, state, max_concurrent=2, timeout=180)
    try:
        assert result['url'] == f"http://127.0.0.1:{result['port']}/OF-R001" and result['running']
        with urllib.request.urlopen(result['url'], timeout=10) as response:
            assert response.status == 200 and b'remotion' in response.read().lower()
        assert studio.session(ep['id'])['running']
        again = studio._start(ep['id'], root, state, max_concurrent=2, timeout=30)
        assert again.get('reused') and again['port'] == result['port']       # no duplicate Studio processes
    finally:
        assert studio.stop(ep['id'])
    assert not studio.session(ep['id'])['running']
