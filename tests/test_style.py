"""Cinematic Flow v1.1 / Classic v1.0 editing profiles. Deterministic: no model usage, no rendering."""
import copy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from services.api import core, creative, media, styles, snapshots, main
from services.api.models import Scene, Package
from .fixtures import IDEA, SCRIPT, NARRATION, package
from .test_station import prepared, asset_fixture

FLOW = styles.FLOW_ID
CLASSIC = styles.CLASSIC_ID


def prepared_with(pkg):
    ep = creative.create_episode(IDEA)
    core.update_episode(ep['id'], 'AWAITING_APPROVAL', script=SCRIPT)
    run = creative.approve(ep['id'], NARRATION)
    creative.complete_run(run['run_id'], pkg, manual=True)
    return core.episode(ep['id'])


def flow_profile():
    return styles.profiles_doc(core.ROOT)['profiles'][FLOW]


def scene(i, text='one two three four five six', **extra):
    return dict(dict(scene_id=f'S{i:03d}', narration_text=text, transition_in='cut', transition_reason='', caption_style='default', emphasis_phrase=''), **extra)


# ----------------------------------------------------------------- profile document
def test_profile_document_is_valid_and_default_is_cinematic_flow():
    doc = styles.profiles_doc(core.ROOT)
    styles.validate_profiles(doc)
    assert doc['default_profile'] == FLOW and set(doc['profiles']) == {CLASSIC, FLOW}
    assert doc['profiles'][CLASSIC]['transitions']['allowed'] == ['cut']  # Classic v1.0 kept, unchanged behaviour
    assert doc['profiles'][FLOW]['transitions']['allowed'] == ['cut', 'crossfade', 'dip_to_dark']
    cfg = doc['profiles'][FLOW]['transitions']
    assert 6 <= cfg['crossfade_frames']['default'] <= 10


@pytest.mark.parametrize('mutation', [
    lambda d: d['invariants'].__setitem__('image_motion', 'animated'),
    lambda d: d['invariants'].__setitem__('sfx', True),
    lambda d: d['profiles'][FLOW]['transitions']['allowed'].append('wipe'),
    lambda d: d['profiles'][FLOW]['transitions']['allowed'].remove('cut'),
    lambda d: d['profiles'][FLOW]['captions'].__setitem__('presets', ['spin']),
    lambda d: d.__setitem__('default_profile', 'MISSING'),
])
def test_profile_document_rejects_policy_violations(mutation):
    doc = copy.deepcopy(styles.profiles_doc(core.ROOT))
    mutation(doc)
    with pytest.raises(ValueError):
        styles.validate_profiles(doc)


def test_skills_loader_pins_rules_and_profiles():
    from services.api import skills
    docs, rules = skills.load_skills()
    assert len(docs) == 4 and rules['version'] == '1.1.0' and rules['editing']['default_profile'] == FLOW
    assert rules['visuals']['image_motion'] == 'static' and rules['audio']['sfx'] is False
    assert rules['audio']['sources'] == ['narration', 'instrumental']


# ----------------------------------------------------------------- scene schema
def test_old_packages_without_style_hints_remain_valid_and_unknown_transitions_are_rejected():
    base = package()['scenes'][0]
    old = {k: v for k, v in base.items() if k not in ('transition_in', 'transition_reason', 'caption_style', 'emphasis_phrase')}
    parsed = Scene.model_validate(old)
    assert parsed.transition_in == 'cut' and parsed.emphasis_phrase == ''
    for bad in ('wipe', 'glitch', 'zoom', 'spin'):
        with pytest.raises(ValidationError):
            Scene.model_validate({**old, 'transition_in': bad})


def test_preproduction_forces_first_cut_and_drops_invalid_emphasis(store):
    pkg = package()
    pkg['scenes'][0]['transition_in'] = 'crossfade'
    pkg['scenes'][0]['emphasis_phrase'] = 'not in this scene at all'
    pkg['scenes'][1]['emphasis_phrase'] = 'door was open'
    ep = prepared_with(pkg)
    scenes = ep['data']['package']['scenes']
    assert scenes[0]['transition_in'] == 'cut' and scenes[0]['emphasis_phrase'] == ''
    assert scenes[1]['emphasis_phrase'] == 'door was open'


# ----------------------------------------------------------------- transitions
def test_transition_budget_first_scene_and_frame_limits():
    profile = flow_profile()
    scenes = [scene(i, transition_in='crossfade') for i in range(1, 13)]
    scenes[3]['transition_in'] = scenes[7]['transition_in'] = scenes[9]['transition_in'] = 'dip_to_dark'
    plan, notes = styles.resolve_transitions(scenes, [90] * 12, profile)
    assert plan[0]['transition'] == 'cut'
    non_cut = [p for p in plan if p['transition'] != 'cut']
    assert len(non_cut) <= int(profile['transitions']['max_non_cut_share'] * 11)
    assert sum(p['transition'] == 'dip_to_dark' for p in plan) <= max(1, int(profile['transitions']['max_dip_share'] * 11))
    assert len(non_cut) < 12 - 1  # never every still
    for p in non_cut:
        spec = profile['transitions']['crossfade_frames' if p['transition'] == 'crossfade' else 'dip_frames']
        assert spec['min'] <= p['frames'] <= spec['max']
    assert any('budget' in n for n in notes)


def test_short_scenes_unknown_names_and_classic_fall_back_to_hard_cuts():
    profile = flow_profile()
    scenes = [scene(1), scene(2, transition_in='crossfade'), scene(3, transition_in='crossfade')]
    plan, notes = styles.resolve_transitions(scenes, [90, 10, 90], profile)
    assert [p['transition'] for p in plan] == ['cut', 'cut', 'cut'] and notes
    plan, notes = styles.resolve_transitions(scenes, [90, 90, 90], profile, overrides={'S002': 'spin-wipe'})
    assert plan[1]['transition'] == 'cut' and any('unknown transition' in n for n in notes)
    plan, notes = styles.resolve_transitions([scene(1), scene(2, transition_in='dip_to_dark')], [90, 90], styles.profiles_doc(core.ROOT)['profiles'][CLASSIC])
    assert plan[1]['transition'] == 'cut' and notes == []


def test_transition_overlap_cannot_exceed_half_of_neighbours():
    profile = flow_profile()
    plan, _ = styles.resolve_transitions([scene(1), scene(2, transition_in='dip_to_dark')], [24, 24], profile)
    assert plan[1]['frames'] <= 24  # each side at most half of the shorter scene
    plan, _ = styles.resolve_transitions([scene(1), scene(2, transition_in='crossfade')], [20, 20], profile)
    assert plan[1]['frames'] <= 10


def test_verify_timeline_rejects_unsafe_plans():
    def props(**kw):
        base = dict(durationInFrames=180, style=dict(allowed_transitions=['cut', 'crossfade', 'dip_to_dark']), captions=[dict(start=0, end=30, enter_frames=7, exit_frames=3)],
                    scenes=[dict(id='S001', start=0, end=90, motion='static', transition='cut', transition_frames=0),
                            dict(id='S002', start=90, end=180, motion='static', transition='crossfade', transition_frames=8)])
        base.update(kw)
        return base
    assert media.verify_timeline(props())
    for mutate in (
        lambda p: p['scenes'][1].update(transition_frames=60),
        lambda p: p['scenes'][1].update(transition='wipe'),
        lambda p: p['scenes'][0].update(transition='crossfade', transition_frames=8),
        lambda p: p['scenes'][1].update(motion='zoom'),
        lambda p: p['scenes'][1].update(start=95),
        lambda p: p.update(durationInFrames=200),
        lambda p: p['captions'][0].update(enter_frames=40),
        lambda p: p['style'].update(allowed_transitions=['cut']),
    ):
        broken = props()
        mutate(broken)
        with pytest.raises(ValueError):
            media.verify_timeline(broken)


# ----------------------------------------------------------------- captions
def test_caption_presets_follow_narrative_function():
    profile = flow_profile()
    pk = [dict(scene_id='S001', narration_text='The key was hanging outside', emphasis_phrase='hanging outside', caption_style='default'),
          dict(scene_id='S002', narration_text='She waited', emphasis_phrase='', caption_style='soft_fade')]
    shots = [dict(id='S001', start=0, end=120), dict(id='S002', start=120, end=200)]
    caps = [dict(start=2, end=30, text='THE KEY WAS'),         # first phrase -> wave reveal
            dict(start=31, end=60, text='HANGING OUTSIDE'),   # emphasised -> glow pop (gold)
            dict(start=61, end=100, text='AND THEN'),         # continuous -> smooth replace (not in narration; no emphasis)
            dict(start=101, end=108, text='NOW'),             # fast -> immediate impact
            dict(start=125, end=170, text='SHE WAITED')]      # soft fade scene
    offsets = [0, 3, 5, 7, 8]
    out = styles.assign_caption_presets(caps, shots, pk, offsets, profile)
    assert [c['preset'] for c in out] == ['wave_reveal', 'glow_pop', 'smooth_replace', 'immediate_impact', 'soft_fade']
    assert out[1]['emphasis'] == 'gold' and all(c['emphasis'] == 'none' for i, c in enumerate(out) if i != 1)
    for c in out:
        dur = c['end'] - c['start']
        assert c['enter_frames'] <= 8 and c['enter_frames'] <= dur * 0.4 + 1 and c['exit_frames'] <= dur
    assert out[3]['enter_frames'] == 0 and out[3]['exit_frames'] == 0
    classic = styles.assign_caption_presets([dict(start=0, end=30, text='A B')], shots[:1], pk[:1], [0], styles.profiles_doc(core.ROOT)['profiles'][CLASSIC])
    assert classic[0]['preset'] == 'quick_pop' and classic[0]['emphasis'] == 'none'


# ----------------------------------------------------------------- episode pinning / isolation
def test_new_episode_inherits_cinematic_flow_and_pins_it(store):
    ep = prepared()
    style = ep['data']['style']
    assert style['profile_id'] == FLOW and style['renderer_dir'] == 'remotion' and style['source'] == 'global_default'
    directory = core.epdir(ep)
    assert (directory / '.production/input_snapshot/brand/EDITING_PROFILES.json').is_file()
    provenance = core.read_json(directory / '.production/provenance.json')
    assert 'brand/EDITING_PROFILES.json' in {r['path'] for r in provenance['files']}
    snapshots.validate(directory)
    effective = styles.effective_style(ep)
    assert effective['profile']['renderer'] == 'cinematic'


def test_global_default_change_never_touches_existing_episodes(store, monkeypatch):
    ep = prepared()
    original = styles.profiles_doc

    def changed(root):
        doc = copy.deepcopy(original(root))
        doc['default_profile'] = CLASSIC
        return doc
    monkeypatch.setattr(styles, 'profiles_doc', changed)
    assert styles.global_default_style(core.ROOT)['profile_id'] == CLASSIC  # global default changed...
    assert core.episode(ep['id'])['data']['style']['profile_id'] == FLOW     # ...the pinned episode did not


def test_legacy_episode_is_classic_and_adoption_is_explicit_and_non_destructive(store):
    ep = prepared()
    directory = core.epdir(ep)
    snapshot = directory / '.production/input_snapshot'
    # Simulate an episode created before editing profiles existed.
    (snapshot / 'brand/EDITING_PROFILES.json').unlink()
    provenance = core.read_json(directory / '.production/provenance.json')
    provenance['files'] = [r for r in provenance['files'] if r['path'] != 'brand/EDITING_PROFILES.json']
    (directory / '.production/provenance.json').write_text(json.dumps(provenance), encoding='utf-8')
    manifest_path = snapshot / 'brand/SKILLS_MANIFEST.json'
    manifest = core.read_json(manifest_path)
    manifest.pop('editing_profiles_sha256', None)
    raw = json.dumps(manifest).encode()
    manifest_path.write_bytes(raw)
    import hashlib
    for r in provenance['files']:
        if r['path'] == 'brand/SKILLS_MANIFEST.json':
            r['sha256'], r['byte_length'] = hashlib.sha256(raw).hexdigest(), len(raw)
    (directory / '.production/provenance.json').write_text(json.dumps(provenance), encoding='utf-8')
    core.update_episode(ep['id'], style=None)
    legacy = core.episode(ep['id'])
    effective = styles.effective_style(legacy)
    assert effective['profile_id'] == CLASSIC and effective['renderer_dir'] == 'remotion' and effective['profile']['transitions']['allowed'] == ['cut']
    before = (snapshot / 'remotion/src/index.tsx').read_bytes()
    with pytest.raises(ValueError, match='Confirm adoption'):
        main.set_style(ep['id'], dict(profile_id=FLOW))          # never automatic
    result = main.set_style(ep['id'], dict(profile_id=FLOW, adopt=True))
    assert result['data']['style']['renderer_dir'] == 'remotion_flow' and result['data']['style']['source'] == 'owner_adopted'
    assert (snapshot / 'remotion/src/index.tsx').read_bytes() == before            # original pin untouched
    assert (snapshot / 'remotion_flow/src/index.tsx').is_file()
    snapshots.validate(directory)                                                   # tamper detection still passes
    assert styles.effective_style(core.episode(ep['id']))['profile']['renderer'] == 'cinematic'
    main.set_style(ep['id'], dict(profile_id=FLOW, adopt=True))                     # idempotent


def test_style_changes_are_per_episode_and_rerender_is_opt_in(store):
    a, b = prepared(), prepared()
    done = core.update_episode(a['id'], 'COMPLETE', exports=[dict(path='x.mp4', job_id=1)])
    out = main.set_style(a['id'], dict(profile_id=CLASSIC))
    assert out['data']['style']['profile_id'] == CLASSIC and out['status'] == 'COMPLETE' and out['data']['exports'] == done['data']['exports']
    assert core.episode(b['id'])['data']['style']['profile_id'] == FLOW           # sibling untouched
    again = main.set_style(a['id'], dict(profile_id=FLOW, rerender=True))
    assert again['status'] == 'AWAITING_ASSETS' and again['data']['exports'] == done['data']['exports']
    core.update_episode(a['id'], 'RENDERING')
    with pytest.raises(ValueError, match='render is in progress'):
        main.set_style(a['id'], dict(profile_id=CLASSIC))


def test_owner_transition_requests_are_validated(store):
    ep = prepared()
    out = main.set_transitions(ep['id'], dict(transitions={'S002': 'crossfade', 'S003': 'cut'}))
    assert out['data']['style_overrides']['transitions'] == {'S002': 'crossfade', 'S003': 'cut'}
    for bad in ({'S001': 'crossfade'}, {'S009': 'cut'}, {'S002': 'wipe'}):
        with pytest.raises(ValueError):
            main.set_transitions(ep['id'], dict(transitions=bad))


# ----------------------------------------------------------------- timeline integration
def test_timeline_uses_pinned_style_and_transitions_never_change_timing(store):
    pkg = package()
    pkg['scenes'][1]['transition_in'] = 'crossfade'
    pkg['scenes'][1]['transition_reason'] = 'Gentle change of focus'
    pkg['scenes'][1]['emphasis_phrase'] = 'door was open'
    ep = prepared_with(pkg)
    asset_fixture(ep)
    report = media.validate_assets(ep['id'])
    assert report['valid'], report['errors']
    flow = media.timeline(ep['id'], report, write=False)
    assert flow['style']['profile_id'] == FLOW and flow['style']['renderer'] == 'cinematic'
    assert flow['scenes'][0]['transition'] == 'cut' and flow['scenes'][1]['transition'] == 'crossfade'
    assert 6 <= flow['scenes'][1]['transition_frames'] <= 10
    assert all(s['motion'] == 'static' for s in flow['scenes'])
    assert any(c['preset'] == 'glow_pop' and c['emphasis'] == 'gold' for c in flow['captions'])
    classic = media.timeline(ep['id'], report, style=styles.preview_style(core.episode(ep['id']), CLASSIC), write=False)
    assert [s['transition'] for s in classic['scenes']] == ['cut'] * 3
    assert {c['preset'] for c in classic['captions']} == {'quick_pop'}
    # Boundaries, duration and caption windows are identical: transitions only layer over unchanged boundaries.
    assert flow['durationInFrames'] == classic['durationInFrames']
    assert [(s['start'], s['end']) for s in flow['scenes']] == [(s['start'], s['end']) for s in classic['scenes']]
    assert [(c['start'], c['end'], c['text']) for c in flow['captions']] == [(c['start'], c['end'], c['text']) for c in classic['captions']]


def test_audio_identity_is_unchanged_by_style(store):
    ep = prepared()
    asset_fixture(ep)
    report = media.validate_assets(ep['id'])
    props = media.timeline(ep['id'], report, write=False)
    assert props['audioSources'] == ['narration', 'instrumental']
    assert 'sfx' not in json.dumps(props).lower()
