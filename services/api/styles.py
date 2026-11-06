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

# Renderer primitives (the renderer contract, unchanged since v1.1) and the editorial vocabulary of
# ODD_FRAME_CINEMATIC_TRANSITIONS_V1. Every editorial name maps onto exactly one primitive.
TRANSITIONS = ('cut', 'crossfade', 'dip_to_dark')
EDITORIAL = ('hard_cut', 'short_crossfade', 'emotional_crossfade', 'dip_to_charcoal', 'graphic_match_cut')
ALL_TRANSITIONS = TRANSITIONS + EDITORIAL
KIND = {'cut': 'cut', 'hard_cut': 'cut', 'graphic_match_cut': 'cut', 'crossfade': 'crossfade', 'short_crossfade': 'crossfade',
        'emotional_crossfade': 'crossfade', 'dip_to_dark': 'dip_to_dark', 'dip_to_charcoal': 'dip_to_dark'}
FRAME_KEYS = {'crossfade': 'crossfade_frames', 'dip_to_dark': 'dip_frames', 'short_crossfade': 'short_crossfade_frames',
              'emotional_crossfade': 'emotional_crossfade_frames', 'dip_to_charcoal': 'dip_frames'}
# Legacy name -> editorial name (and back) so hints written for one profile stay meaningful under the other.
TO_EDITORIAL = {'cut': 'hard_cut', 'crossfade': 'short_crossfade', 'dip_to_dark': 'dip_to_charcoal'}
CAPTION_PRESETS = ('quick_pop', 'wave_reveal', 'glow_pop', 'smooth_replace', 'immediate_impact', 'soft_fade')
CLASSIC_ID = 'ODD_FRAME_CLASSIC_V1_0'
FLOW_ID = 'ODD_FRAME_CINEMATIC_FLOW_V1_1'
TRANSITIONS_ID = 'ODD_FRAME_CINEMATIC_TRANSITIONS_V1'
PROFILES_PATH = 'brand/EDITING_PROFILES.json'
DECISIONS_PATH = '06_edit/transition_decisions.json'


def normalize_transition(name, allowed):
    """Map a requested name onto one the profile allows (legacy <-> editorial). None if impossible."""
    if name in allowed:
        return name
    if name in TO_EDITORIAL and TO_EDITORIAL[name] in allowed:
        return TO_EDITORIAL[name]
    if name in KIND and KIND[name] in allowed:
        return KIND[name]
    return None

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
        if not ({'cut', 'hard_cut'} & set(allowed)) or any(t not in ALL_TRANSITIONS for t in allowed):
            raise ValueError(key + ': transitions must be known names (' + ', '.join(ALL_TRANSITIONS) + ') and include a hard cut')
        for name in allowed:
            if KIND[name] != 'cut' and not p['transitions'].get(FRAME_KEYS[name]):
                raise ValueError(key + ': ' + name + ' needs ' + FRAME_KEYS[name])
        for name in set(FRAME_KEYS.values()):
            spec = p['transitions'].get(name)
            if spec and not (1 <= spec['min'] <= spec['default'] <= spec['max'] <= 30):
                raise ValueError(key + ': ' + name + ' must satisfy 1 <= min <= default <= max <= 30')
        for share in ('max_non_cut_share', 'max_dip_share', 'max_emotional_share'):
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


def _pinned_docs(ep_directory):
    """The episode's originally pinned profile document first, then later owner-adopted profile documents
    (``brand/EDITING_PROFILES.<version>.<sha>.json``). An id pinned earlier always keeps its original definition."""
    base = snapshot_dir(ep_directory)
    docs = [profiles_doc(base)] + [read_json(p) for p in sorted((base / 'brand').glob('EDITING_PROFILES.*.json'))] if (base / 'brand').is_dir() else [profiles_doc(base)]
    return [d for d in docs if d]


def available_profiles(ep_directory):
    merged = {}
    for doc in _pinned_docs(ep_directory):
        for key, value in doc['profiles'].items():
            merged.setdefault(key, value)
    return merged or {CLASSIC_ID: LEGACY_CLASSIC}


def effective_style(ep):
    """The episode's pinned profile. Never reads global configuration."""
    from .core import epdir
    directory = epdir(ep)
    style = ep['data'].get('style') or {}
    doc = profiles_doc(snapshot_dir(directory))
    profiles = available_profiles(directory)
    pid = style.get('profile_id') or (doc['default_profile'] if doc else CLASSIC_ID)
    if pid not in profiles:
        pid = CLASSIC_ID
    profile = copy.deepcopy(profiles[pid])
    return dict(profile=profile, profile_id=pid, version=profile['version'], renderer_dir=style.get('renderer_dir', 'remotion'),
                source=style.get('source', 'legacy'), doc_sha256=style.get('doc_sha256'))


def _frames(spec, wanted, limit):
    frames = min(max(spec['min'], wanted if wanted else spec['default']), spec['max'])
    return min(frames, limit)


_TIME_WORDS = re.compile(r"\b(later|hours?|days?|weeks?|months?|years?|morning|night|midnight|dawn|dusk|evening|tomorrow|yesterday|eventually|by the time|that night|after a while|silence|waited|waiting)\b", re.I)
_SHOCK_WORDS = re.compile(r"\b(suddenly|crash(?:ed)?|scream(?:ed)?|slam(?:med)?|shatter(?:ed)?|gone|snapped|burst|ran|grabbed|but|however|instead|nothing|empty|wrong)\b", re.I)


_QUIET_WORDS = re.compile(r"\b(whisper(?:ed)?|softly|gently|quietly|smile[sd]?|remember(?:ed)?|memory|tears?|trust(?:ed)?|alone|miss(?:ed)?|love[sd]?|hug(?:ged)?|held|holding|goodbye|finally)\b", re.I)


def suggest_transitions(package_scenes):
    """Deterministic fallback when no AI/owner transition decisions exist (never random, never a quota).

    Dialogue turns, shocks, contrasts, changes of cast and actions -> hard cut (the default). Time passing ->
    dip to charcoal. The same characters continuing a quiet, emotional moment -> emotional crossfade; the same
    characters simply continuing -> short crossfade. A graphic match cut is never guessed: it needs someone to have
    looked at the artwork. Returns editorial names; the pinned profile maps/limits them afterwards."""
    out = {}
    for i in range(1, len(package_scenes)):
        prev, cur = package_scenes[i - 1], package_scenes[i]
        text = cur.get('narration_text', '')
        same_cast = set(prev.get('character_ids') or []) == set(cur.get('character_ids') or [])
        if _SHOCK_WORDS.search(text) or not same_cast or text.lstrip().startswith(('"', '“')):
            continue
        if _TIME_WORDS.search(text):
            out[cur['scene_id']] = ('dip_to_charcoal', 'Auto: time passes or a quiet pause')
        elif _QUIET_WORDS.search(text):
            out[cur['scene_id']] = ('emotional_crossfade', 'Auto: the same characters continue a quiet emotional moment')
        else:
            out[cur['scene_id']] = ('short_crossfade', 'Auto: the same characters continue the moment')
    return out


def load_decisions(directory, package_scenes):
    """Validated per-boundary transition decisions for this episode (AI editorial plan, editor or owner), or None.

    Strict: every boundary exactly once and in order, only the five supported names, integer frame counts.
    Anything else is rejected (never silently fixed); no code or free-form renderer input is accepted."""
    from .models import TransitionPlan
    path = Path(directory) / DECISIONS_PATH
    if not path.is_file():
        return None
    plan = TransitionPlan.model_validate(read_json(path)).model_dump()
    ids = [s['scene_id'] for s in package_scenes]
    expected = list(zip(ids, ids[1:]))
    found = [(d['from_scene'], d['to_scene']) for d in plan['decisions']]
    if found != expected:
        raise ValueError(f'{DECISIONS_PATH} must list every scene boundary exactly once, in order ({len(expected)} boundaries)')
    for d in plan['decisions']:
        if KIND[d['transition']] == 'cut' and d['duration_frames'] != 0:
            raise ValueError(f"{d['from_scene']}→{d['to_scene']}: {d['transition']} has zero frames")
        if KIND[d['transition']] != 'cut' and d['duration_frames'] < 1:
            raise ValueError(f"{d['from_scene']}→{d['to_scene']}: {d['transition']} needs a frame count")
    return plan


def resolve_transitions(package_scenes, scene_frames, profile, overrides=None, decisions=None):
    """Return ([{transition, editorial, frames, reason, purpose, source}], notes) for every scene (index 0: none).

    `transition` is the renderer primitive (cut/crossfade/dip_to_dark); `editorial` the profile's name for it.
    Priority: owner overrides > per-boundary decisions file > storyboard (AI) hints > deterministic fallback.
    Everything is only a request: names the pinned profile does not allow, scenes too short to overlap safely, frame
    counts outside the profile range and the share guardrails are applied here and reported as notes."""
    cfg = profile['transitions']
    allowed = list(cfg['allowed'])
    cut_name = 'hard_cut' if 'hard_cut' in allowed else 'cut'
    overrides = overrides or {}
    n = len(package_scenes)
    notes = []
    first = dict(transition='cut', editorial=cut_name, frames=0, reason='first scene', purpose='', source='rule')
    if {KIND[a] for a in allowed} == {'cut'}:
        return [first] + [dict(transition='cut', editorial=cut_name, frames=0, reason='', purpose='', source='profile') for _ in range(n - 1)], notes
    by_target = {d['to_scene']: d for d in (decisions or {}).get('decisions', [])}
    suggested = {}
    if not overrides and not by_target and not any(sc.get('transition_in', 'cut') not in ('cut', 'hard_cut') for sc in package_scenes):
        suggested = suggest_transitions(package_scenes)
        notes.append('Transitions suggested automatically from the narration (deterministic fallback: no transition decisions were authored for this episode)')
    # Guardrails, not quotas: at least one of each permitted kind is always possible in a short reel.
    share = lambda key: max(1 if cfg.get(key, 0) > 0 else 0, int(round(cfg.get(key, 0) * max(0, n - 1))))
    max_non_cut = share('max_non_cut_share')
    max_dips, max_emotional = share('max_dip_share'), share('max_emotional_share') if 'max_emotional_share' in cfg else n
    non_cut = dips = emotional = 0
    out = [first]
    for i in range(1, n):
        sc = package_scenes[i]
        sid = sc['scene_id']
        frames_wanted, purpose = None, ''
        if sid in overrides:
            o = overrides[sid]
            wanted, reason, source = (o.get('transition'), o.get('reason', ''), 'owner') if isinstance(o, dict) else (o, 'Owner choice', 'owner')
            frames_wanted = o.get('frames') if isinstance(o, dict) else None
        elif sid in by_target:
            d = by_target[sid]
            wanted, reason, purpose, frames_wanted, source = d['transition'], d['narrative_reason'], d.get('narrative_purpose', ''), d['duration_frames'] or None, 'decisions'
        elif sid in suggested:
            (wanted, reason), source = suggested[sid], 'fallback'
        else:
            wanted, reason, source = sc.get('transition_in', 'cut'), sc.get('transition_reason', '') or '', 'storyboard'
        result = dict(transition='cut', editorial=cut_name, frames=0, reason=reason, purpose=purpose, source=source)
        name = normalize_transition(wanted, allowed) if wanted in ALL_TRANSITIONS else None
        if wanted not in ALL_TRANSITIONS:
            notes.append(f"{sid}: unknown transition '{wanted}' replaced by a hard cut")
        elif name is None:
            notes.append(f"{sid}: {wanted} is not available in {profile['label']}; hard cut used")
        elif KIND[name] == 'cut':
            result['editorial'] = name
        else:
            kind = KIND[name]
            shorter = min(scene_frames[i - 1], scene_frames[i])
            spec = cfg[FRAME_KEYS[name]]
            # Share guardrails stop automatic/AI suggestions from over-using effects. A reviewed per-boundary
            # editorial decision (decisions file or owner) is not overruled by a percentage: narrative suitability wins.
            guarded = source in ('storyboard', 'fallback')
            if shorter < cfg.get('min_scene_frames_for_transition', 18):
                notes.append(f"{sid}: neighbouring scene too short for {name}; hard cut used")
            elif guarded and non_cut >= max_non_cut:
                notes.append(f"{sid}: transition budget (guardrail) reached ({max_non_cut}); hard cut used")
            elif guarded and kind == 'dip_to_dark' and dips >= max_dips:
                notes.append(f"{sid}: dip budget (guardrail) reached ({max_dips}); hard cut used")
            elif guarded and name == 'emotional_crossfade' and emotional >= max_emotional:
                notes.append(f"{sid}: emotional-crossfade budget (guardrail) reached ({max_emotional}); hard cut used")
            elif frames_wanted and not spec['min'] <= frames_wanted <= spec['max']:
                notes.append(f"{sid}: {name} must be {spec['min']}-{spec['max']} frames (got {frames_wanted}); hard cut used")
            else:
                # Each side of the boundary may use at most half of the shorter neighbouring scene.
                frames = _frames(spec, frames_wanted, shorter // 2 * (1 if kind == 'crossfade' else 2))
                if frames < spec['min']:
                    notes.append(f"{sid}: not enough frames for {name}; hard cut used")
                else:
                    result.update(transition=kind, editorial=name, frames=frames)
                    non_cut += 1
                    dips += kind == 'dip_to_dark'
                    emotional += name == 'emotional_crossfade'
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
                renderer_dir=style['renderer_dir'],
                # The renderer only ever sees primitives; editorial names never reach it.
                allowed_transitions=[k for k in TRANSITIONS if k in {KIND[a] for a in p['transitions']['allowed']}],
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
    if profile_id in available_profiles(directory):
        wanted = wanted[1:]          # already pinned (originally or by an earlier adoption): keep that exact definition
    for relative, source in wanted:
        raw = source.read_bytes()
        record = existing.get(relative)
        if record and record['sha256'] != sha(raw) and relative == PROFILES_PATH:
            # A newer profile document: pinned NEXT to the original one, which is never rewritten.
            relative = f"brand/EDITING_PROFILES.{doc['profiles'][profile_id]['version']}.{sha(raw)[:12]}.json"
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
    pinned_profiles = available_profiles(directory)
    if profile_id in pinned_profiles:
        profile = copy.deepcopy(pinned_profiles[profile_id])
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
