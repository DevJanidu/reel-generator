"""Versioned editing profiles (Classic v1.0 / Cinematic Flow v1.1).

Pure, deterministic logic shared by the controller and the isolated worker:
* validation of the global profile document,
* per-episode pinned style resolution (a global default change never touches an existing episode),
* validated scene-transition resolution and caption preset assignment.

Stills are static in every profile; only scene transitions and typography differ.
"""
import copy
import os
import re
from pathlib import Path
from .core import ROOT, now, sha, read_json

TRANSITIONS = ('cut', 'crossfade', 'dip_to_dark')
CAPTION_PRESETS = ('quick_pop', 'wave_reveal', 'glow_pop', 'smooth_replace', 'immediate_impact', 'soft_fade')
CLASSIC_ID = 'ODD_FRAME_CLASSIC_V1_0'
FLOW_ID = 'ODD_FRAME_CINEMATIC_FLOW_V1_1'
PROFILES_PATH = 'brand/EDITING_PROFILES.json'

# Episodes created before profiles existed carry no profile document; they behave exactly as Classic v1.0.
LEGACY_CLASSIC = dict(id=CLASSIC_ID, label='Classic v1.0', version='1.0.0', renderer='classic',
                      transitions=dict(allowed=['cut']),
                      captions=dict(presets=['quick_pop'], entrance='quick_pop', replace='quick_pop',
                                    emphasis='quick_pop', fast='quick_pop', glow=False))


def clean_words(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.lower().replace('’', "'"))


def validate_profiles(doc):
    """Raise ValueError unless the profile document keeps every non-negotiable invariant."""
    inv = doc.get('invariants') or {}
    if inv.get('image_motion') != 'static' or inv.get('generated_video') or inv.get('character_animation') or inv.get('sfx'):
        raise ValueError('Editing profiles must keep static stills, no generated video, no character animation and no SFX')
    if inv.get('audio_sources') != ['narration', 'instrumental']:
        raise ValueError('Editing profiles must keep exactly narration + instrumental')
    profiles = doc.get('profiles') or {}
    if doc.get('default_profile') not in profiles:
        raise ValueError('Default editing profile is not defined')
    for key, p in profiles.items():
        if p.get('id') != key or not p.get('version') or p.get('renderer') not in ('classic', 'cinematic'):
            raise ValueError('Invalid editing profile identity: ' + str(key))
        allowed = (p.get('transitions') or {}).get('allowed') or []
        if 'cut' not in allowed or any(t not in TRANSITIONS for t in allowed):
            raise ValueError(key + ': transitions must be a subset of cut/crossfade/dip_to_dark and include cut')
        for name in ('crossfade_frames', 'dip_frames'):
            spec = p['transitions'].get(name)
            if spec and not (1 <= spec['min'] <= spec['default'] <= spec['max'] <= 30):
                raise ValueError(key + ': ' + name + ' must satisfy 1 <= min <= default <= max <= 30')
        for share in ('max_non_cut_share', 'max_dip_share'):
            if share in p['transitions'] and not 0 <= p['transitions'][share] <= 1:
                raise ValueError(key + ': ' + share + ' must be between 0 and 1')
        caps = p.get('captions') or {}
        if any(x not in CAPTION_PRESETS for x in caps.get('presets', [])):
            raise ValueError(key + ': unknown caption preset')
        for role in ('entrance', 'replace', 'emphasis', 'fast'):
            if caps.get(role) not in caps.get('presets', []):
                raise ValueError(key + ': caption role ' + role + ' must reference an enabled preset')
        if p['renderer'] == 'cinematic':
            wave = caps.get('wave') or {}
            if not (1 <= wave.get('entrance_frames', 0) <= 8):
                raise ValueError(key + ': wave entrance must be 1-8 frames')
    return doc


def snapshot_dir(ep_directory):
    return Path(ep_directory) / '.production/input_snapshot'


def profiles_doc(root):
    path = Path(root) / PROFILES_PATH
    return read_json(path) if path.is_file() else None


def global_default_style(source_root=ROOT):
    doc = profiles_doc(source_root)
    if not doc:
        return dict(profile_id=CLASSIC_ID, version='1.0.0', doc_sha256=None, renderer_dir='remotion', source='legacy')
    validate_profiles(doc)
    default = doc['default_profile']
    return dict(profile_id=default, version=doc['profiles'][default]['version'],
                doc_sha256=sha((Path(source_root) / PROFILES_PATH).read_bytes()), renderer_dir='remotion', source='global_default', pinned_at=now())


def available_profiles(ep_directory):
    doc = profiles_doc(snapshot_dir(ep_directory))
    return doc['profiles'] if doc else {CLASSIC_ID: LEGACY_CLASSIC}


def effective_style(ep):
    """The episode's pinned profile. Never reads global configuration."""
    from .core import epdir
    directory = epdir(ep)
    style = ep['data'].get('style') or {}
    doc = profiles_doc(snapshot_dir(directory))
    profiles = doc['profiles'] if doc else {CLASSIC_ID: LEGACY_CLASSIC}
    pid = style.get('profile_id') or (doc['default_profile'] if doc else CLASSIC_ID)
    if pid not in profiles:
        pid = CLASSIC_ID
    profile = copy.deepcopy(profiles[pid])
    return dict(profile=profile, profile_id=pid, version=profile['version'], renderer_dir=style.get('renderer_dir', 'remotion'),
                source=style.get('source', 'legacy'), doc_sha256=style.get('doc_sha256'))


def _frames(spec, wanted, limit):
    frames = min(max(spec['min'], wanted if wanted else spec['default']), spec['max'])
    return min(frames, limit)


def resolve_transitions(package_scenes, scene_frames, profile, overrides=None):
    """Return ([{transition, frames, reason}], notes) for every scene (index 0 is always a cut).

    Deterministic and validated: the AI/owner request is only a request. Anything not allowed by the pinned profile,
    too short to overlap safely, or beyond the share limits is downgraded to a hard cut and reported."""
    cfg = profile['transitions']
    allowed = set(cfg['allowed'])
    overrides = overrides or {}
    n = len(package_scenes)
    notes = []
    if allowed == {'cut'}:
        return [dict(transition='cut', frames=0, reason='') for _ in range(n)], notes
    max_non_cut = int(cfg.get('max_non_cut_share', 0) * max(0, n - 1))
    max_dips = max(1 if cfg.get('max_dip_share', 0) > 0 else 0, int(cfg.get('max_dip_share', 0) * max(0, n - 1)))
    non_cut = dips = 0
    out = [dict(transition='cut', frames=0, reason='first scene')]
    for i in range(1, n):
        sc = package_scenes[i]
        wanted = overrides.get(sc['scene_id'], sc.get('transition_in', 'cut'))
        reason = sc.get('transition_reason', '') or ''
        result = dict(transition='cut', frames=0, reason=reason)
        if wanted not in TRANSITIONS:
            notes.append(f"{sc['scene_id']}: unknown transition '{wanted}' replaced by a hard cut")
        elif wanted != 'cut':
            shorter = min(scene_frames[i - 1], scene_frames[i])
            if wanted not in allowed:
                notes.append(f"{sc['scene_id']}: {wanted} is not available in {profile['label']}; hard cut used")
            elif shorter < cfg.get('min_scene_frames_for_transition', 18):
                notes.append(f"{sc['scene_id']}: neighbouring scene too short for {wanted}; hard cut used")
            elif non_cut >= max_non_cut:
                notes.append(f"{sc['scene_id']}: transition budget reached ({max_non_cut}); hard cut used")
            elif wanted == 'dip_to_dark' and dips >= max_dips:
                notes.append(f"{sc['scene_id']}: dip budget reached ({max_dips}); hard cut used")
            else:
                spec = cfg['crossfade_frames'] if wanted == 'crossfade' else cfg['dip_frames']
                # Each side of the boundary may use at most half of the shorter neighbouring scene.
                frames = _frames(spec, None, shorter // 2 * (1 if wanted == 'crossfade' else 2))
                if frames < spec['min']:
                    notes.append(f"{sc['scene_id']}: not enough frames for {wanted}; hard cut used")
                else:
                    result = dict(transition=wanted, frames=frames, reason=reason)
                    non_cut += 1
                    dips += wanted == 'dip_to_dark'
        out.append(result)
    return out, notes


def assign_caption_presets(captions, scenes, package_scenes, offsets, profile):
    """Choose a caption preset per phrase by narrative function (never randomly).

    `offsets[i]` is the first narration-word index of captions[i]; scenes carry (start_word, end_word)."""
    caps = profile['captions']
    classic = profile['renderer'] == 'classic'
    wave = caps.get('wave') or {}
    glow_cfg = caps.get('glow_style') or {}
    scene_words = {}
    word = 0
    for ps in package_scenes:
        count = len(clean_words(ps['narration_text']))
        scene_words[ps['scene_id']] = (word, word + count, ps)
        word += count
    previous = None
    for i, cap in enumerate(captions):
        dur = cap['end'] - cap['start']
        n_words = len(clean_words(cap['text']))
        cap['words'] = n_words
        if classic:
            cap.update(preset='quick_pop', emphasis='none', enter_frames=5, exit_frames=0, glow=False)
            continue
        scene_id = next((s['id'] for s in scenes if s['start'] <= cap['start'] < s['end']), None)
        lo, hi, ps = scene_words.get(scene_id, (0, 0, {}))
        emphasized = False
        phrase = clean_words(ps.get('emphasis_phrase', '') or '')
        if phrase:
            narration = clean_words(ps['narration_text'])
            for j in range(0, len(narration) - len(phrase) + 1):
                if narration[j:j + len(phrase)] == phrase:
                    a, b = lo + j, lo + j + len(phrase)
                    emphasized = offsets[i] < b and offsets[i] + n_words > a
                    break
        gap = cap['start'] - previous['end'] if previous else 999
        if dur < caps.get('fast_phrase_frames', 10):
            preset = caps['fast']
        elif emphasized:
            preset = caps['emphasis']
        elif ps.get('caption_style') == 'soft_fade' and 'soft_fade' in caps['presets']:
            preset = 'soft_fade'
        elif previous and gap <= 2:
            preset = caps['replace']
        else:
            preset = caps['entrance']
        enter = 0 if preset == 'immediate_impact' else min(wave.get('entrance_frames', 7), int(dur * wave.get('max_entrance_share', .4)))
        exit_ = 0 if preset in ('immediate_impact', 'glow_pop') else min(wave.get('exit_frames', 3), int(dur * .25))
        if preset == 'immediate_impact':
            enter = exit_ = 0
        cap.update(preset=preset, emphasis='gold' if emphasized else 'none', enter_frames=max(0, enter), exit_frames=max(0, exit_),
                   glow=bool(caps.get('glow')))
        previous = cap
    return captions


def renderer_style(style, notes):
    """The only style data the renderer receives (already validated; no AI-authored names pass through)."""
    p = style['profile']
    return dict(profile_id=style['profile_id'], version=style['version'], renderer=p['renderer'],
                renderer_dir=style['renderer_dir'], allowed_transitions=p['transitions']['allowed'],
                dip_color=p['transitions'].get('dip_color', '#14171C'),
                wave=(p['captions'].get('wave') or {}), glow=(p['captions'].get('glow_style') or {}),
                min_glow_frames=p['captions'].get('min_glow_frames', 14), notes=notes)


def pin_style_upgrade(directory, profile_id=FLOW_ID, source_root=ROOT):
    """Owner-triggered: pin the current profile document + renderer next to an OLD episode's snapshot.

    Controller/development only. The original pinned files are untouched; new files are added and recorded in the
    provenance so tamper detection keeps working. Approved script, stills and narration are not touched."""
    if os.getenv('ODD_EPISODE_WORKER') == '1':
        raise ValueError('Workers cannot adopt a style profile')
    import json
    from .file_writer import EpisodeWriter, parent_handles
    from .snapshots import validate
    directory = Path(directory)
    provenance = validate(directory)
    doc_path = Path(source_root) / PROFILES_PATH
    doc = read_json(doc_path)
    validate_profiles(doc)
    if profile_id not in doc['profiles']:
        raise ValueError('Unknown editing profile')
    writer = EpisodeWriter(directory)
    wanted = [(PROFILES_PATH, doc_path), ('remotion_flow/src/index.tsx', Path(source_root) / 'video/remotion/src/index.tsx'),
              ('remotion_flow/src/composition.tsx', Path(source_root) / 'video/remotion/src/composition.tsx'),
              ('remotion_flow/render.mjs', Path(source_root) / 'video/remotion/render.mjs')]
    existing = {r['path']: r for r in provenance['files']}
    for relative, source in wanted:
        raw = source.read_bytes()
        record = existing.get(relative)
        if record:
            if record['sha256'] != sha(raw):
                raise ValueError('This episode already pinned a different version of ' + relative)
            continue
        writer.bytes('.production/input_snapshot/' + relative, raw, immutable=True)
        provenance['files'].append(dict(source='Owner-triggered style adoption', path=relative, sha256=sha(raw), byte_length=len(raw)))
    destination = directory / '.production/provenance.json'
    with parent_handles(destination):
        temporary = destination.with_suffix('.pending')
        temporary.write_text(json.dumps(provenance, indent=2), encoding='utf-8')
        temporary.replace(destination)
    return dict(profile_id=profile_id, version=doc['profiles'][profile_id]['version'], doc_sha256=sha(doc_path.read_bytes()),
                renderer_dir='remotion_flow', source='owner_adopted', pinned_at=now())


def preview_style(ep, profile_id):
    """Style used ONLY for Preview Style. A profile the episode has not pinned is previewed with the shared
    (read-only) current renderer/profile document; nothing is pinned or saved for the episode."""
    from .core import epdir
    pinned = effective_style(ep)
    directory = epdir(ep)
    doc = profiles_doc(snapshot_dir(directory))
    if doc and profile_id in doc['profiles']:
        profile = copy.deepcopy(doc['profiles'][profile_id])
        renderer_dir = pinned['renderer_dir']
        pinned_here = True
    elif profile_id == CLASSIC_ID:
        profile = copy.deepcopy(LEGACY_CLASSIC)
        renderer_dir = pinned['renderer_dir']
        pinned_here = True
    else:
        shared = profiles_doc(ROOT)
        if not shared or profile_id not in shared['profiles']:
            raise ValueError('Unknown editing profile: ' + str(profile_id))
        validate_profiles(shared)
        profile = copy.deepcopy(shared['profiles'][profile_id])
        renderer_dir = '@app'
        pinned_here = False
    return dict(profile=profile, profile_id=profile_id, version=profile['version'], renderer_dir=renderer_dir,
                source='preview', doc_sha256=None, pinned_here=pinned_here)
