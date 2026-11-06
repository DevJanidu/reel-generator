"""ODD_FRAME_CINEMATIC_TRANSITIONS_V1: narrative-aware scene transitions. Deterministic: no model usage, no MP4 render."""
import copy
import hashlib
import json
import pytest
from pydantic import ValidationError
from services.api import core, editor, media, snapshots, studio, styles, worker, main
from services.api.models import TransitionPlan
from .test_station import prepared, asset_fixture

NEW = styles.TRANSITIONS_ID


def profile():
    return styles.profiles_doc(core.ROOT)['profiles'][NEW]


def scene(i, text='one two three four five six', cast=('A',), **extra):
    return {**dict(scene_id=f'S{i:03d}', narration_text=text, character_ids=list(cast), transition_in='hard_cut', transition_reason=''), **extra}


def decision(a, b, name='hard_cut', frames=0, reason='Immediate reaction'):
    return dict(from_scene=f'S{a:03d}', to_scene=f'S{b:03d}', transition=name, duration_frames=frames, narrative_reason=reason)


def plan(decisions):
    return dict(profile_id=NEW, version='1.0.0', author='test editor', created='2026-11-06T00:00:00Z', decisions=decisions)


# ----------------------------------------------------------------- profile
def test_profile_defines_the_five_editorial_transitions_with_the_requested_durations():
    p = profile()
    t = p['transitions']
    assert t['allowed'] == ['hard_cut', 'short_crossfade', 'emotional_crossfade', 'dip_to_charcoal', 'graphic_match_cut']
    assert t['short_crossfade_frames'] == dict(min=5, default=7, max=8)
    assert t['emotional_crossfade_frames']['default'] == 11 and t['dip_frames']['default'] == 12 and t['dip_color'] == '#14171C'
    assert p['renderer'] == 'cinematic' and p['captions']['glow'] is True and p['captions']['wave']['entrance_frames'] <= 8
    # The renderer never sees editorial names, only its unchanged primitives.
    style = styles.renderer_style(dict(profile=p, profile_id=NEW, version='1.0.0', renderer_dir='remotion'), [])
    assert style['allowed_transitions'] == ['cut', 'crossfade', 'dip_to_dark']


def test_profile_validation_rejects_moving_or_unknown_transitions():
    doc = copy.deepcopy(styles.profiles_doc(core.ROOT))
    doc['profiles'][NEW]['transitions']['allowed'].append('slide')
    with pytest.raises(ValueError):
        styles.validate_profiles(doc)
    doc = copy.deepcopy(styles.profiles_doc(core.ROOT))
    del doc['profiles'][NEW]['transitions']['emotional_crossfade_frames']
    with pytest.raises(ValueError, match='needs emotional_crossfade_frames'):
        styles.validate_profiles(doc)


# ----------------------------------------------------------------- decisions schema
def test_decision_schema_is_strict():
    TransitionPlan.model_validate(plan([decision(1, 2)]))
    for bad in (dict(transition='wipe'), dict(transition='cut'), dict(duration_frames=7.5), dict(duration_frames=-1),
                dict(code='<Sequence/>'), dict(from_scene='../S001')):
        with pytest.raises(ValidationError):
            TransitionPlan.model_validate(plan([{**decision(1, 2), **bad}]))
    with pytest.raises(ValidationError):
        TransitionPlan.model_validate({**plan([decision(1, 2)]), 'profile_id': 'OTHER'})


def test_decisions_must_cover_every_boundary_in_order(tmp_path):
    scenes = [scene(i) for i in (1, 2, 3)]
    path = tmp_path / styles.DECISIONS_PATH
    path.parent.mkdir(parents=True)
    for decisions, message in (([decision(1, 2)], 'every scene boundary'), ([decision(2, 3), decision(1, 2)], 'every scene boundary'),
                               ([decision(1, 2, frames=4), decision(2, 3)], 'zero frames'),
                               ([decision(1, 2, 'short_crossfade', 0), decision(2, 3)], 'needs a frame count')):
        path.write_text(json.dumps(plan(decisions)), encoding='utf-8')
        with pytest.raises(ValueError, match=message):
            styles.load_decisions(tmp_path, scenes)
    path.write_text(json.dumps(plan([decision(1, 2, 'graphic_match_cut'), decision(2, 3, 'dip_to_charcoal', 12, 'Time jump')])), encoding='utf-8')
    assert len(styles.load_decisions(tmp_path, scenes)['decisions']) == 2


# ----------------------------------------------------------------- resolution
def test_decisions_drive_the_plan_and_profile_limits_still_apply():
    scenes = [scene(i) for i in range(1, 7)]
    decisions = plan([decision(1, 2, 'graphic_match_cut', 0, 'Hook shape matches the claw'),
                      decision(2, 3, 'short_crossfade', 7, 'Quiet continuity'),
                      decision(3, 4, 'emotional_crossfade', 11, 'Memory'),
                      decision(4, 5, 'dip_to_charcoal', 12, 'Time jump'),
                      decision(5, 6, 'short_crossfade', 20, 'Too long')])
    out, notes = styles.resolve_transitions(scenes, [120] * 6, profile(), decisions=decisions)
    assert [(p['transition'], p['editorial'], p['frames']) for p in out] == [
        ('cut', 'hard_cut', 0), ('cut', 'graphic_match_cut', 0), ('crossfade', 'short_crossfade', 7),
        ('crossfade', 'emotional_crossfade', 11), ('dip_to_dark', 'dip_to_charcoal', 12), ('cut', 'hard_cut', 0)]
    assert out[3]['reason'] == 'Memory' and out[3]['source'] == 'decisions'
    assert any('must be 5-8 frames' in n for n in notes)               # out-of-range request rejected, not stretched
    # Owner overrides beat the decisions file; a short neighbour can never hold an overlap.
    out, _ = styles.resolve_transitions(scenes, [120] * 6, profile(), overrides={'S003': 'hard_cut'}, decisions=decisions)
    assert out[2]['editorial'] == 'hard_cut' and out[2]['source'] == 'owner'
    out, notes = styles.resolve_transitions(scenes, [120, 120, 10, 120, 120, 120], profile(), decisions=decisions)
    assert out[2]['transition'] == 'cut' and any('too short' in n for n in notes)


def test_v11_hints_map_onto_the_new_names_and_back():
    scenes = [scene(1), scene(2, transition_in='crossfade'), scene(3, transition_in='dip_to_dark')] + [scene(i) for i in range(4, 9)]
    out, _ = styles.resolve_transitions(scenes, [120] * 8, profile())
    assert [p['editorial'] for p in out[:4]] == ['hard_cut', 'short_crossfade', 'dip_to_charcoal', 'hard_cut']
    # Storyboard (AI) hints stay under the share guardrail: 2 of 2 boundaries in a 3-scene reel is too many.
    out, notes = styles.resolve_transitions(scenes[:3], [120] * 3, profile())
    assert [p['transition'] for p in out].count('cut') == 2 and any('guardrail' in n for n in notes)
    flow = styles.profiles_doc(core.ROOT)['profiles'][styles.FLOW_ID]
    out, _ = styles.resolve_transitions([scene(1), scene(2, transition_in='emotional_crossfade'), scene(3, transition_in='graphic_match_cut')], [120] * 3, flow)
    assert [(p['transition'], p['editorial']) for p in out] == [('cut', 'cut'), ('crossfade', 'crossfade'), ('cut', 'cut')]


def test_deterministic_fallback_is_editorial_not_random():
    scenes = [scene(1, 'She found the key.'),
              scene(2, 'She kept looking at it.'),                       # same cast continues -> short crossfade
              scene(3, 'Hours later, nothing had changed.'),             # time jump... but "nothing" is a shock word -> cut
              scene(4, 'He smiled softly and held her paw.'),            # quiet emotional moment -> emotional crossfade
              scene(5, '"Why?" she asked.'),                             # dialogue turn -> cut
              scene(6, 'Suddenly the door slammed.'),                    # shock -> cut
              scene(7, 'A stranger arrived.', cast=('B',)),              # change of cast -> cut
              scene(8, 'By morning the hall was quiet.', cast=('B',))]   # time passing -> dip
    out, notes = styles.resolve_transitions(scenes, [120] * 8, profile())
    assert [p['editorial'] for p in out] == ['hard_cut', 'short_crossfade', 'hard_cut', 'emotional_crossfade', 'hard_cut', 'hard_cut', 'hard_cut', 'dip_to_charcoal']
    assert 'graphic_match_cut' not in {p['editorial'] for p in out}      # never guessed without looking at the artwork
    assert styles.resolve_transitions(scenes, [120] * 8, profile()) == (out, notes)
    assert any('suggested automatically' in n for n in notes)


# ----------------------------------------------------------------- episode integration (timeline + Studio source)
def draft_with_decisions(store, monkeypatch, decisions_for):
    monkeypatch.setattr(editor, 'STORE', store)
    monkeypatch.setattr(studio, 'STORE', store)
    ep = prepared()
    root = asset_fixture(ep)
    ids = [s['scene_id'] for s in core.episode(ep['id'])['data']['package']['scenes']]
    (root / styles.DECISIONS_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / styles.DECISIONS_PATH).write_text(json.dumps(plan(decisions_for(ids))), encoding='utf-8')
    jid = worker.enqueue(ep['id'])
    monkeypatch.setenv('ODD_EPISODE_WORKER', '1')
    monkeypatch.setenv('EPISODE_WRITE_ROOT', str(root))
    editor.prepare(ep['id'], jid)
    monkeypatch.delenv('ODD_EPISODE_WORKER')
    monkeypatch.delenv('EPISODE_WRITE_ROOT')
    with core.db() as c:
        c.execute("UPDATE jobs SET status='COMPLETE' WHERE id=?", (jid,))
    return ep, root


def crossfade_then_dip(ids):
    return [dict(from_scene=ids[0], to_scene=ids[1], transition='short_crossfade', duration_frames=7, narrative_reason='Quiet continuity'),
            dict(from_scene=ids[1], to_scene=ids[2], transition='dip_to_charcoal', duration_frames=12, narrative_reason='Time jump')]


def test_transitions_never_change_timing_and_studio_source_is_frame_exact(store, monkeypatch):
    ep, root = draft_with_decisions(store, monkeypatch, crossfade_then_dip)
    m = studio.manifest(root)
    shots = m['scenes']
    assert [(s['editorial'], s['transition_frames']) for s in shots] == [('hard_cut', 0), ('short_crossfade', 7), ('dip_to_charcoal', 12)]
    # Same boundaries, duration and captions as a plan with only hard cuts.
    report = media.validate_assets(ep['id'])
    cuts = media.timeline(ep['id'], report, write=False, extra_overrides={s['id']: 'hard_cut' for s in shots[1:]})
    assert [(s['start'], s['end']) for s in shots] == [(s['start'], s['end']) for s in cuts['scenes']]
    assert m['durationInFrames'] == cuts['durationInFrames']
    source = (studio.studio_dir(root) / 'src/Episode.tsx').read_text(encoding='utf-8')
    assert '<TransitionSeries name=' in source and source.count('<TransitionSeries.Transition') == 2
    assert 'presentation={crossfade()} timing={transitionTiming(7)}' in source
    assert 'presentation={dipToCharcoal(STYLE.dip_color)} timing={transitionTiming(12)}' in source
    check = studio.check_source(root)
    assert check['errors'] == [] and check['warnings'] == []
    # The series is exactly the narration length and every transition midpoint is the narration boundary.
    assert check['scenes'][-1]['end'] == m['durationInFrames'] == check['total_frames']
    assert [(t['to'], t['boundary']) for t in check['transitions']] == [(s['id'], s['start']) for s in shots[1:]]
    # Captions are absolute (continuous layer), identical to the measured plan.
    caps = core.read_json(root / '06_edit/captions.json')
    import re
    found = [(int(a), int(a) + int(b)) for a, b in re.findall(r'name=\{"CAP\d{3}[^"]*"\} from=\{(\d+)\} durationInFrames=\{(\d+)\}', source)]
    assert found == [(c['start'], c['end']) for c in caps]


def test_source_policy_for_transition_series(store, monkeypatch):
    ep, root = draft_with_decisions(store, monkeypatch, crossfade_then_dip)
    path = studio.studio_dir(root) / 'src/Episode.tsx'
    original = path.read_text(encoding='utf-8')
    cases = [
        (original.replace("import {TransitionSeries} from '@remotion/transitions';",
                          "import {TransitionSeries} from '@remotion/transitions';\nimport {slide} from '@remotion/transitions/slide';"), 'no slide, wipe'),
        (original.replace('presentation={crossfade()}', 'presentation={slide()}'), 'other than crossfade'),
        (original.replace('timing={transitionTiming(7)}', 'timing={myTiming}'), 'literal frame count'),
        (original.replace('timing={transitionTiming(12)}', 'timing={transitionTiming(45)}'), '1-30 frames'),
    ]
    for text, expected in cases:
        path.write_text(text, encoding='utf-8')
        assert expected in ' '.join(studio.check_source(root)['errors']), expected
    # Moving a boundary (lengthen one still, shorten the next) keeps the length but is reported.
    import re
    durations = [int(x) for x in re.findall(r'<TransitionSeries\.Sequence name=\{"[^"]*"\} durationInFrames=\{(\d+)\}', original)]
    moved = original.replace(f'durationInFrames={{{durations[0]}}}', f'durationInFrames={{{durations[0] + 6}}}', 1)
    moved = moved.replace(f'durationInFrames={{{durations[1]}}}', f'durationInFrames={{{durations[1] - 6}}}', 1)
    path.write_text(moved, encoding='utf-8')
    check = studio.check_source(root)
    assert check['errors'] == [] and any('instead of its narration boundary' in w for w in check['warnings'])


def test_owner_can_migrate_an_episode_pinned_to_an_older_profile_document(store):
    ep = prepared()
    directory = core.epdir(ep)
    snapshot = directory / '.production/input_snapshot'
    # Simulate an episode pinned before v1 existed: its profile document lacks the new profile.
    doc_path = snapshot / 'brand/EDITING_PROFILES.json'
    old = core.read_json(doc_path)
    del old['profiles'][NEW]
    old['default_profile'] = styles.FLOW_ID
    raw = json.dumps(old).encode()
    doc_path.write_bytes(raw)
    manifest_path = snapshot / 'brand/SKILLS_MANIFEST.json'
    manifest = core.read_json(manifest_path)
    manifest['editing_profiles_sha256'] = hashlib.sha256(raw).hexdigest()
    manifest_raw = json.dumps(manifest).encode()
    manifest_path.write_bytes(manifest_raw)
    provenance = core.read_json(directory / '.production/provenance.json')
    for r in provenance['files']:
        if r['path'] == 'brand/EDITING_PROFILES.json':
            r['sha256'], r['byte_length'] = hashlib.sha256(raw).hexdigest(), len(raw)
        if r['path'] == 'brand/SKILLS_MANIFEST.json':
            r['sha256'], r['byte_length'] = hashlib.sha256(manifest_raw).hexdigest(), len(manifest_raw)
    (directory / '.production/provenance.json').write_text(json.dumps(provenance), encoding='utf-8')
    core.update_episode(ep['id'], style=dict(profile_id=styles.FLOW_ID, version='1.1.0', renderer_dir='remotion', source='global_default'))
    assert NEW not in styles.available_profiles(directory)
    with pytest.raises(ValueError, match='Confirm adoption'):
        main.set_style(ep['id'], dict(profile_id=NEW))
    out = main.set_style(ep['id'], dict(profile_id=NEW, adopt=True))
    assert out['data']['style']['profile_id'] == NEW
    assert doc_path.read_bytes() == raw                                      # original pin never rewritten
    assert list((snapshot / 'brand').glob('EDITING_PROFILES.1.0.0.*.json'))  # new document pinned next to it
    snapshots.validate(directory)
    effective = styles.effective_style(core.episode(ep['id']))
    assert effective['profile_id'] == NEW and effective['profile']['transitions']['allowed'][0] == 'hard_cut'
    assert styles.available_profiles(directory)[styles.FLOW_ID] == old['profiles'][styles.FLOW_ID]
    main.set_style(ep['id'], dict(profile_id=NEW, adopt=True))               # idempotent
