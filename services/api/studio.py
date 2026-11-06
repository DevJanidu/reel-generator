"""Official Remotion Studio integration.

Per episode a self-contained, source-authored Remotion project is generated under ``06_edit/studio``:

    src/index.ts, Root.tsx, Episode.tsx   generated once; Root/Episode are then OWNED by the owner (Studio saves into them)
    src/lib/*                             pinned copy of the shared ODD FRAME effect components (never edited in production)
    src/style.ts, src/envelope.ts         generated data (profile parameters, narration envelope for ducking)
    public/images|audio                   copies of the episode's own media (Studio's --public-dir; nothing else is served)
    studio.manifest.json                  hashes, provenance, source revision, the editing contract

The Studio *source* is the single source of truth for the final render. Regeneration never overwrites owner edits
without an explicit request and always archives the previous source under ``studio/revisions``.
"""
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from .core import ROOT, STORE, now, read_json
from .file_writer import EpisodeWriter

STUDIO_DIR = '06_edit/studio'
LIB_FILES = ('composition.tsx', 'library.tsx')
EDITABLE = ('src/Episode.tsx', 'src/Root.tsx')
GENERATED = ('src/index.ts', 'src/style.ts', 'src/envelope.ts', 'remotion.config.ts', 'tsconfig.json', 'package.json')
STAGES = ['Checking assets', 'Loading storyboard', 'Preparing timeline', 'Generating Studio composition', 'Registering scenes',
          'Adding captions', 'Attaching narration', 'Attaching signature instrumental', 'Validating composition',
          'Starting Remotion Studio', 'Ready to edit']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def composition_id(code):
    """Remotion composition ids allow letters, digits and hyphens only."""
    return re.sub(r'[^A-Za-z0-9-]', '-', code)


def _ts(value):
    return json.dumps(value, ensure_ascii=False)


def _short_title(text, words=4):
    pieces = re.findall(r"[A-Za-z0-9']+", text or '')
    return ' '.join(pieces[:words]).title() if pieces else ''


def _style_ts(style):
    keys = ('profile_id', 'version', 'renderer', 'allowed_transitions', 'dip_color', 'wave', 'glow', 'min_glow_frames')
    picked = {k: style[k] for k in keys if k in style}
    if 'wave' in picked:   # only the fields the renderer's StyleProps declares (keeps the project type-clean)
        picked['wave'] = {k: v for k, v in picked['wave'].items() if k in ('entrance_frames', 'stagger_total_frames', 'rise_px', 'exit_frames')}
    return ("import type {StyleProps} from './lib/library';\n"
            f"export const STYLE: StyleProps = {json.dumps(picked, indent=2)};\n")


def _episode_tsx(code, props, package_scenes):
    total = props['durationInFrames']
    scenes = props['scenes']
    titles = {s['scene_id']: _short_title(s.get('beat', '')) for s in package_scenes}
    lines = []
    add = lines.append
    add("import React from 'react';")
    add("import {Sequence, staticFile} from 'remotion';")
    add("import {TransitionSeries} from '@remotion/transitions';")
    add("import {z} from 'zod';")
    add("import {CaptionSwitcher, crossfade, dipToCharcoal, MusicTrack, NarrationTrack, StaticStoryScene, StudioStage, transitionTiming} from './lib/library';")
    add("import {STYLE} from './style';")
    add("import {ENVELOPE} from './envelope';")
    add('')
    add('/*')
    add(' * ODD FRAME — source-authored episode composition for the official Remotion Studio.')
    add(' * Every still, transition, caption and audio source is its own named Sequence on purpose, so it appears')
    add(' * as a separate item in the Studio timeline. This file is yours once generated: edit it in Studio or in')
    add(' * your editor. ODD FRAME will not overwrite it without asking, and archives it before any regeneration.')
    add(' * Stills are static (no zoom/pan). Exactly two audio sources: narration + signature instrumental.')
    add(' */')
    add('export const episodeSchema = z.object({')
    add('  audio: z.object({')
    add('    narration_gain: z.number().min(0).max(2).step(0.01),')
    add('    music_gain: z.number().min(0).max(2).step(0.01),')
    add('    fade_in: z.number().int().min(0).max(300),')
    add('    fade_out: z.number().int().min(0).max(300),')
    add('    ducking: z.number().min(0).max(1).step(0.05),')
    add('  }),')
    add('  caption: z.object({glow_strength: z.number().min(0).max(2).step(0.05)}),')
    add('});')
    add('export type EpisodeProps = z.infer<typeof episodeSchema>;')
    add(f'export const TOTAL_FRAMES = {total};')
    add('')
    add('export const Episode: React.FC<EpisodeProps> = ({audio, caption}) => (')
    add('  <StudioStage>')
    add('    {/* ── STORY ILLUSTRATIONS + SCENE TRANSITIONS ──────────────────────────────────────────────')
    add('         Official @remotion/transitions TransitionSeries. A transition overlaps its two neighbours, so every')
    add('         still carries half of each neighbouring transition as a handle: the midpoint of every transition sits')
    add('         exactly on the narration-grounded scene boundary and the series is exactly TOTAL_FRAMES long.')
    add('         Captions, narration and music below are separate absolute layers and never move with the stills.')
    add('         Allowed: crossfade() and dipToCharcoal() from ./lib/library; hard / graphic-match cuts have no element. */}')
    add('    <TransitionSeries name={"STORY — stills + transitions"}>')
    for i, shot in enumerate(scenes):
        nxt = scenes[i + 1] if i + 1 < len(scenes) else None
        t_in = (shot.get('transition_frames') or 0) if i > 0 and shot['transition'] != 'cut' else 0
        t_out = (nxt.get('transition_frames') or 0) if nxt and nxt['transition'] != 'cut' else 0
        start = shot['start'] - t_in // 2
        end = shot['end'] + (t_out - t_out // 2)
        if i > 0:
            editorial = shot.get('transition_editorial') or shot['transition']
            why = (shot.get('transition_reason') or '').replace('*/', '* /')
            add(f"      {{/* {scenes[i - 1]['id']} → {shot['id']} · {editorial.replace('_', ' ')}"
                f"{f' ({t_in} frames)' if t_in else ''} · boundary frame {shot['start']}{' · ' + why if why else ''} */}}")
            if shot['transition'] == 'crossfade' and t_in:
                add(f"      <TransitionSeries.Transition presentation={{crossfade()}} timing={{transitionTiming({t_in})}} />")
            elif shot['transition'] == 'dip_to_dark' and t_in:
                add(f"      <TransitionSeries.Transition presentation={{dipToCharcoal(STYLE.dip_color)}} timing={{transitionTiming({t_in})}} />")
        title = titles.get(shot['id'], '')
        label = f"{shot['id']} — {title}" if title else shot['id']
        add(f"      <TransitionSeries.Sequence name={{{_ts(label)}}} durationInFrames={{{end - start}}} premountFor={{30}}>")
        add(f"        <StaticStoryScene src={{staticFile('images/{shot['id']}.png')}} />")
        add('      </TransitionSeries.Sequence>')
    add('    </TransitionSeries>')
    add('    {/* ── ANIMATED CAPTIONS (continuous layer above the stills; narration-synchronised) ─────── */}')
    for n, cap in enumerate(props['captions'], 1):
        text = cap['text']
        label = f"CAP{n:03d} — {text.upper()[:40]}"
        add(f"    <Sequence name={{{_ts(label)}}} from={{{cap['start']}}} durationInFrames={{{cap['end'] - cap['start']}}}>")
        attrs = [f"text={{{_ts(text)}}}", f"y={{{round(cap['y'], 3)}}}", f"preset={{{_ts(cap['preset'])}}}"]
        if cap.get('emphasis', 'none') != 'none':
            attrs.append(f"emphasis={{{_ts(cap['emphasis'])}}}")
        attrs.append(f"enter_frames={{{cap.get('enter_frames', 0)}}}")
        attrs.append(f"exit_frames={{{cap.get('exit_frames', 0)}}}")
        if cap.get('size', 1) != 1:
            attrs.append(f"size={{{cap['size']}}}")
        if cap.get('glow', True) is False:
            attrs.append('glow={false}')
        attrs.append(f"glow_strength={{{round(cap.get('glow_strength', 1), 3)} * caption.glow_strength}}")
        attrs.append('style={STYLE}')
        add('      <CaptionSwitcher ' + ' '.join(attrs) + ' />')
        add('    </Sequence>')
    add('    {/* ── AUDIO: narration + signature instrumental (no sound effects) ── */}')
    add('    <Sequence name={"NARRATION — ElevenLabs"} from={0} durationInFrames={TOTAL_FRAMES} layout="none">')
    add("      <NarrationTrack src={staticFile('audio/narration.wav')} gain={audio.narration_gain} />")
    add('    </Sequence>')
    add('    <Sequence name={"MUSIC — Signature Instrumental"} from={0} durationInFrames={TOTAL_FRAMES} layout="none">')
    add("      <MusicTrack src={staticFile('audio/instrumental.wav')} audio={audio} envelope={ENVELOPE} totalFrames={TOTAL_FRAMES} />")
    add('    </Sequence>')
    add('  </StudioStage>')
    add(');')
    return '\n'.join(lines) + '\n'


def _root_literal(comp_id, default):
    body = re.sub(r'"(\w+)":', r'\1:', json.dumps(default, indent=2)).replace('\n', '\n    ')
    return ("import React from 'react';\n"
            "import {Composition} from 'remotion';\n"
            "import {Episode, episodeSchema, TOTAL_FRAMES} from './Episode';\n\n"
            "export const Root: React.FC = () => (\n"
            "  <Composition\n"
            f"    id={_ts(comp_id)}\n"
            "    component={Episode}\n"
            "    schema={episodeSchema}\n"
            "    width={1080}\n    height={1920}\n    fps={30}\n"
            "    durationInFrames={TOTAL_FRAMES}\n"
            f"    defaultProps={{{body}}}\n"
            "  />\n);\n")


CONFIG_TS = """import {Config} from '@remotion/cli/config';
import path from 'node:path';

// Generated by ODD FRAME. Shared dependencies come from the application's node_modules; nothing is installed per episode.
Config.setEntryPoint('./src/index.ts');
Config.setPublicDir('./public');
Config.setOverwriteOutput(false);
const appRoot = process.env.ODD_APP_ROOT;
if (appRoot) {
  Config.overrideWebpackConfig((config) => ({
    ...config,
    resolve: {
      ...config.resolve,
      modules: [path.join(appRoot, 'node_modules'), 'node_modules'],
    },
  }));
}
"""

TSCONFIG = json.dumps({"compilerOptions": {"target": "ES2022", "module": "ESNext", "moduleResolution": "bundler", "jsx": "react-jsx",
                                           "strict": True, "skipLibCheck": True, "noEmit": True}, "include": ["src"]}, indent=2) + '\n'
PACKAGE_JSON = json.dumps({"name": "odd-frame-episode-studio", "private": True, "version": "0.0.0", "type": "module"}, indent=2) + '\n'
INDEX_TS = "import {registerRoot} from 'remotion';\nimport {Root} from './Root';\n\nregisterRoot(Root);\n"


def studio_dir(directory):
    return Path(directory) / STUDIO_DIR


def manifest(directory):
    path = studio_dir(directory) / 'studio.manifest.json'
    return read_json(path) if path.is_file() else None


def owner_changes(directory):
    """Editable files that no longer match what ODD FRAME generated (i.e. the owner has edited them in Studio)."""
    m = manifest(directory)
    if not m:
        return []
    changed = []
    for rel in EDITABLE:
        path = studio_dir(directory) / rel
        if not path.is_file() or sha(path.read_bytes()) != m['files'][rel]:
            changed.append(rel)
    return changed


def _archive(directory, writer, label):
    base = studio_dir(directory)
    stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + label
    for rel in EDITABLE + ('studio.manifest.json',):
        source = base / rel
        if source.is_file():
            writer.bytes(f'{STUDIO_DIR}/revisions/{stamp}/{rel}', source.read_bytes(), replace=False)
    return stamp


def generate(directory, props, package_scenes, code, *, force=False, source_revision=None, media_root=None, emit=None):
    """Create/refresh the Studio project from a validated auto-edit. Returns the manifest.

    Owner-edited sources are never replaced unless ``force`` is set, and are archived first either way."""
    directory = Path(directory)
    media_root = Path(media_root) if media_root else STORE
    writer = EpisodeWriter(directory)
    existing = manifest(directory)
    changed = owner_changes(directory) if existing else []
    if existing and changed and not force:
        raise ValueError('The Studio project has your edits in ' + ', '.join(changed) + '. They were kept. '
                         'Regenerate only if you want to replace them (the current version is archived first).')
    say = emit or (lambda *a, **k: None)
    archived = _archive(directory, writer, 'before-regenerate') if existing else None
    comp = composition_id(code)
    say('Generating Studio composition', 'Writing source-authored composition and effect library')
    for name in LIB_FILES:
        writer.bytes(f'{STUDIO_DIR}/src/lib/{name}', (ROOT / 'video/remotion/src' / name).read_bytes())
    files = {
        'src/index.ts': INDEX_TS, 'src/style.ts': _style_ts(props['style']),
        'src/envelope.ts': 'export const ENVELOPE: number[] = ' + json.dumps([round(v, 3) for v in props['audio']['envelope']]) + ';\n',
        'remotion.config.ts': CONFIG_TS, 'tsconfig.json': TSCONFIG, 'package.json': PACKAGE_JSON,
        'src/Episode.tsx': _episode_tsx(code, props, package_scenes), 'src/Root.tsx': _root_literal(
            comp, {'audio': {k: props['audio'][k] for k in ('narration_gain', 'music_gain', 'fade_in', 'fade_out', 'ducking')},
                   'caption': {'glow_strength': 1}}),
    }
    for rel, text in files.items():
        writer.text(f'{STUDIO_DIR}/{rel}', text)
    say('Registering scenes', f"{len(props['scenes'])} stills registered as named sequences")
    media = {}
    for shot in props['scenes']:
        raw = (media_root / shot['image']).read_bytes()
        writer.bytes(f"{STUDIO_DIR}/public/images/{shot['id']}.png", raw)
        media[f"images/{shot['id']}.png"] = dict(origin=shot['image'], sha256=sha(raw))
    say('Adding captions', f"{len(props['captions'])} narration-synchronised caption phrases added")
    for name, source in (('barlow-condensed-800.woff2', 'node_modules/@fontsource/barlow-condensed/files/barlow-condensed-latin-800-normal.woff2'),
                         ('atkinson-hyperlegible-next-600.woff2', 'node_modules/@fontsource/atkinson-hyperlegible-next/files/atkinson-hyperlegible-next-latin-600-normal.woff2')):
        raw = (ROOT / source).read_bytes()
        writer.bytes(f'{STUDIO_DIR}/public/fonts/{name}', raw)
        media['fonts/' + name] = dict(origin=source, sha256=sha(raw))
    say('Attaching narration', 'Copying the normalized ElevenLabs narration')
    raw = (media_root / props['narration']).read_bytes()
    writer.bytes(f'{STUDIO_DIR}/public/audio/narration.wav', raw)
    media['audio/narration.wav'] = dict(origin=props['narration'], sha256=sha(raw))
    say('Attaching signature instrumental', 'Copying the pinned signature instrumental')
    raw = (media_root / props['instrumental']).read_bytes()
    writer.bytes(f'{STUDIO_DIR}/public/audio/instrumental.wav', raw)
    media['audio/instrumental.wav'] = dict(origin=props['instrumental'], sha256=sha(raw))
    lib = {name: sha((ROOT / 'video/remotion/src' / name).read_bytes()) for name in LIB_FILES}
    file_hashes = {rel: sha(text.encode('utf-8')) for rel, text in files.items()}
    m = dict(version=1, created=now(), composition_id=comp, episode_code=code, width=1080, height=1920, fps=30,
             durationInFrames=props['durationInFrames'], source_editor_revision=source_revision, style=dict(
                 profile_id=props['style']['profile_id'], version=props['style']['version']),
             scenes=[dict(id=s['id'], start=s['start'], end=s['end'], transition=s['transition'], transition_frames=s.get('transition_frames', 0),
                          editorial=s.get('transition_editorial', s['transition']), reason=s.get('transition_reason', ''),
                          source=s.get('transition_source', ''))
                     for s in props['scenes']],
             timeline='transition_series',
             captions=len(props['captions']), files=file_hashes, library=lib, media=media, editable=list(EDITABLE),
             previous_source_archived_as=archived, remotion_version=_remotion_version())
    if props.get('storytelling_metadata'):m['storytelling_metadata']=props['storytelling_metadata']
    writer.json(f'{STUDIO_DIR}/studio.manifest.json', m)
    say('Validating composition', 'Checking the generated project structure')
    validate_project(directory)
    return m


def _remotion_version():
    return read_json(ROOT / 'node_modules/remotion/package.json')['version']


def validate_project(directory):
    """Cheap structural validation (the real compile check happens when Studio/the renderer bundles it)."""
    base = studio_dir(directory)
    m = manifest(directory)
    if not m:
        raise ValueError('No Studio project has been generated for this episode yet')
    for rel in GENERATED + tuple(f'src/lib/{n}' for n in LIB_FILES) + EDITABLE:
        if not (base / rel).is_file():
            raise ValueError('Studio project file is missing: ' + rel)
    for name, digest in m['library'].items():
        if sha((base / 'src/lib' / name).read_bytes()) != digest:
            raise ValueError('The pinned effect library in this Studio project was modified: ' + name)
    for rel, entry in m['media'].items():
        path = base / 'public' / rel
        if not path.is_file() or sha(path.read_bytes()) != entry['sha256']:
            raise ValueError('Studio media is missing or changed: ' + rel + '. Regenerate the Studio project to refresh it.')
    source = (base / 'src/Episode.tsx').read_text(encoding='utf-8')
    root_src = (base / 'src/Root.tsx').read_text(encoding='utf-8')
    if 'staticFile(' not in source or m['composition_id'] not in root_src:
        raise ValueError('Studio composition is missing its media or registration')
    if re.search(r'<Audio\b', source) or 'NarrationTrack' not in source or 'MusicTrack' not in source:
        raise ValueError('Exactly the narration and signature instrumental are allowed as audio sources')
    return m


# ------------------------------------------------------------------ source policy (what the final render trusts)
def _strip_strings(text):
    text = re.sub(r"/\*.*?\*/", '', text, flags=re.S)
    double = r'"(?:\\.|[^"\\])*"'
    single = r"'(?:\\.|[^'\\])*'"
    backtick = r'`(?:\\.|[^`\\])*`'
    text = re.sub('|'.join((double, single, backtick)), '""', text)
    return re.sub(r'//[^\n]*', '', text)


def check_source(directory):
    """Parse the (possibly owner-edited) Studio source and enforce the ODD FRAME production rules.

    Returns dict(scenes, captions, audio, errors, warnings). Errors block the final render; warnings are shown to the owner."""
    base = studio_dir(directory)
    raw = (base / 'src/Episode.tsx').read_text(encoding='utf-8')
    code = _strip_strings(raw)
    errors, warnings = [], []
    m = manifest(directory)
    total_match = re.search(r'TOTAL_FRAMES\s*=\s*(\d+)', raw)
    total = int(total_match.group(1)) if total_match else (m or {}).get('durationInFrames', 0)
    items = []
    for tag in re.finditer(r'<Sequence\b(.*?)>', raw, flags=re.S):
        attrs = tag.group(1)
        name = re.search(r'name=\{?"((?:[^"\\]|\\.)*)"\}?', attrs)
        start = re.search(r'from=\{(-?\d+)\}', attrs)
        dur = re.search(r'durationInFrames=\{(\d+)\}', attrs)
        if name and name.group(1).startswith(('NARRATION', 'MUSIC')):
            items.append(dict(name=name.group(1), start=0, end=total))  # full-length by construction (TOTAL_FRAMES)
            continue
        if not (name and start and dur):
            warnings.append('A Sequence has non-literal timing and could not be checked: ' + (name.group(1) if name else 'unnamed'))
            continue
        items.append(dict(name=json.loads('"' + name.group(1) + '"'), start=int(start.group(1)), end=int(start.group(1)) + int(dur.group(1))))
    transitions = []
    series = re.search(r'<TransitionSeries(?![.\w])(.*?)</TransitionSeries>', raw, flags=re.S)
    if re.search(r'''from\s+['"]@remotion/transitions/''', raw):
        errors.append('Only the ODD FRAME presentations from ./lib/library are allowed (no slide, wipe, flip, cube or other moving transitions).')
    if series:
        pos, previous, pending = 0, None, 0
        for tag in re.finditer(r'<TransitionSeries\.(Sequence|Transition)\b(.*?)/?>', series.group(1), flags=re.S):
            kind, attrs = tag.group(1), tag.group(2)
            if kind == 'Transition':
                presentation = re.search(r'presentation=\{\s*(crossfade\(\s*\)|dipToCharcoal\([^)]*\))\s*\}', attrs)
                timing = re.search(r'timing=\{\s*transitionTiming\(\s*(\d+)\s*\)\s*\}', attrs)
                if not presentation:
                    errors.append('A scene transition uses a presentation other than crossfade() or dipToCharcoal(): not allowed.')
                if not timing:
                    errors.append('A scene transition must use timing={transitionTiming(<frames>)} with a literal frame count.')
                    continue
                frames = int(timing.group(1))
                if previous is None or pending:
                    errors.append('A transition must sit between two stills.')
                    continue
                if not 1 <= frames <= 30 or frames > previous['end'] - previous['start']:
                    errors.append(f"The transition after {previous['name'].split(' ')[0]} is {frames} frames: it must be 1-30 frames and fit inside both stills.")
                pending = frames
                pos -= frames
                continue
            name = re.search(r'name=\{?"((?:[^"\\]|\\.)*)"\}?', attrs)
            dur = re.search(r'durationInFrames=\{(\d+)\}', attrs)
            label = json.loads('"' + name.group(1) + '"') if name else 'unnamed'
            if not dur or re.search(r'\boffset=', attrs):
                errors.append('Still sequence timing must be a literal durationInFrames (no offset): ' + label)
                continue
            item = dict(name=label, start=pos, end=pos + int(dur.group(1)), transition_in=pending)
            if pending and pending > item['end'] - item['start']:
                errors.append(f"The transition before {label.split(' ')[0]} is longer than that still.")
            if previous is not None:
                transitions.append(dict(to=label.split(' ')[0], frames=pending, boundary=item['start'] + pending // 2))
            items.append(item)
            pos, previous, pending = item['end'], item, 0
        if pending:
            errors.append('The story ends with a transition that has no following still.')
    scenes = sorted((i for i in items if re.match(r'S\d{3}\b', i['name'])), key=lambda i: (i['start'], i['name']))
    planned = {s['id']: s['start'] for s in (m or {}).get('scenes', [])}
    for t in transitions:
        if t['to'] in planned and t['boundary'] != planned[t['to']]:
            warnings.append(f"{t['to']} now changes at frame {t['boundary']} instead of its narration boundary {planned[t['to']]} "
                            f"({t['boundary'] - planned[t['to']]:+d} frames). Check that the picture still matches the narration.")
    captions = [i for i in items if re.match(r'CAP\d+', i['name'])]
    audio = [i for i in items if i['name'].startswith(('NARRATION', 'MUSIC'))]
    expected = len((m or {}).get('scenes', scenes))
    if len(scenes) != expected:
        errors.append(f'Expected {expected} story-illustration sequences, found {len(scenes)}: every approved still must remain.')
    if not scenes:
        errors.append('No story illustration sequences were found.')
    if scenes:
        if scenes[0]['start'] > 0:
            errors.append(f"The first still starts at frame {scenes[0]['start']}; frames before it would be empty.")
        reach = scenes[0]['end']
        for scene in scenes[1:]:
            if scene['start'] > reach:
                errors.append(f"Gap before {scene['name'].split(' ')[0]}: frames {reach}-{scene['start']} show no still (black frames are not allowed).")
            reach = max(reach, scene['end'])
        if reach < total:
            errors.append(f'The last still ends at frame {reach} but the video is {total} frames long.')
        elif reach > total:
            errors.append(f'The stills run to frame {reach} but the video (narration) is {total} frames long: shorten a still so nothing is cut off.')
    if re.search(r'<\s*(Audio|Video|OffthreadVideo|Html5Audio|Html5Video)\b', code):
        errors.append('Audio/video elements outside the two intended sources are not allowed (narration + signature instrumental only, no sound effects).')
    if re.search(r'\b(translate|translateX|translateY|rotate|scale|transform|zoom|interpolate|spring|keyframes?)\b', code):
        errors.append('Image movement is prohibited: stills must stay static (no pan, zoom, rotation, scale, offset or keyframe animation on scenes).')
    if len([a for a in audio if a['name'].startswith('NARRATION')]) != 1 or len([a for a in audio if a['name'].startswith('MUSIC')]) != 1:
        errors.append('Exactly one narration and one signature-instrumental sequence are required.')
    for cap in captions:
        if cap['end'] > total:
            warnings.append(f"{cap['name'].split(' ')[0]} extends past the end of the video.")
    if not captions:
        errors.append('Center captions are mandatory.')
    return dict(scenes=scenes, captions=len(captions), audio=audio, total_frames=total, transitions=transitions, errors=errors, warnings=warnings)


# ------------------------------------------------------------------ Studio process management (trusted controller)
_lock = threading.Lock()
_running = {}  # eid -> dict(proc, job, port, url, started)
_starting = {}  # eid -> thread


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _http_ready(port, timeout=2):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=timeout) as r:
            return r.status == 200
    except OSError:
        return False


def launch_file(directory):
    return Path(directory) / '.production/studio_launch.json'


def _log(directory, state, stage, message, **extra):
    """Real, timestamped launch events for the dashboard (nothing here is estimated)."""
    state.setdefault('events', []).append(dict(stage=stage, message=message, at=now()))
    state.update(stage=stage, message=message, updated=now(), **extra)
    path = launch_file(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding='utf-8')


def launch_state(directory):
    path = launch_file(directory)
    return read_json(path) if path.is_file() else None


def session(eid):
    """Current Studio session if its process is alive and answering HTTP."""
    with _lock:
        info = _running.get(eid)
        if info and info['proc'].poll() is None and _http_ready(info['port']):
            return dict(running=True, port=info['port'], url=info['url'], pid=info['proc'].pid, started=info['started'])
        if info and info['proc'].poll() is not None:
            _running.pop(eid, None)
    return dict(running=False)


def _kill(proc):
    try:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        proc.kill()


def stop(eid):
    with _lock:
        info = _running.pop(eid, None)
    if not info:
        return False
    _kill(info['proc'])
    info['job'].close()
    return True


def stop_all():
    for eid in list(_running):
        stop(eid)


def is_starting(eid):
    t = _starting.get(eid)
    return bool(t and t.is_alive())


def begin_start(eid, directory, *, max_concurrent=2, timeout=240):
    """Start (or reuse) the official Studio in the background; progress goes to .production/studio_launch.json."""
    directory = Path(directory)
    if is_starting(eid):
        return dict(started=False, reason='already starting')
    state = dict(status='STARTING', events=[], started=now())
    _log(directory, state, 'Checking assets', 'Verifying the saved Studio project and its media')

    def work():
        try:
            result = _start(eid, directory, state, max_concurrent=max_concurrent, timeout=timeout)
            _log(directory, state, 'Ready to edit', f"Remotion Studio Ready at {result['url']}", status='READY', url=result['url'], port=result['port'])
        except Exception as exc:  # reported verbatim to the owner, with Retry
            _log(directory, state, 'Failed', str(exc), status='FAILED', error=str(exc))
    thread = threading.Thread(target=work, name=f'studio-start-{eid}', daemon=True)
    _starting[eid] = thread
    thread.start()
    return dict(started=True)


def _start(eid, directory, state, *, max_concurrent, timeout):
    m = validate_project(directory)
    check = check_source(directory)
    if check['errors']:
        raise ValueError('The Studio source breaks a production rule: ' + ' '.join(check['errors']))
    live = session(eid)
    if live['running']:
        return dict(live, composition_id=m['composition_id'], reused=True)
    with _lock:
        others = [k for k, v in _running.items() if k != eid and v['proc'].poll() is None]
    while len(others) >= max_concurrent:  # bound resources: stop the longest-running other Studio
        stop(others.pop(0))
    cli = ROOT / 'node_modules/@remotion/cli/remotion-cli.js'
    if not cli.is_file():
        raise ValueError('The official Remotion CLI is not installed (npm install @remotion/cli).')
    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js was not found on PATH.')
    port = _free_port()
    base = studio_dir(directory)
    logs = directory / '.production/logs'
    logs.mkdir(parents=True, exist_ok=True)
    temp = directory / '.production/temp/studio'
    temp.mkdir(parents=True, exist_ok=True)
    log_path = logs / f'studio-{port}.log'
    out = log_path.open('wb')
    # Permission boundary: Studio must write its own source, so it runs in the same verified Windows MXC sandbox as the
    # production workers: write access only to THIS episode folder; shared code, other episodes, data/ and .env are
    # read-only or denied. If the boundary cannot be verified the Studio is not started (and is never called "isolated").
    from . import isolation
    from .file_writer import assert_clean_tree
    assert_clean_tree(directory)
    isolation.require_verified(directory)
    # Fixed executable + validated argument list; the only variable is a verified free loopback port.
    inner = [node, str(cli), 'studio', 'src/index.ts', '--port', str(port), '--no-open', '--public-dir', 'public', '--disable-git-source']
    argv = isolation.sandbox_argv(directory, inner, network=True)
    argv[argv.index('-C') + 1] = str(base)  # Remotion resolves its project root from the working directory
    env = isolation.environment(directory, f'studio-{port}')
    env.update(ODD_APP_ROOT=str(ROOT), BROWSER='none')
    _log(directory, state, 'Starting Remotion Studio', f'Starting the official Remotion Studio on 127.0.0.1:{port} inside the episode sandbox. The first launch compiles the project.')
    started = time.time()
    proc = subprocess.Popen(argv, cwd=base, env=env, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    from .windows_job import ProcessJob
    job = ProcessJob(proc)  # the Studio dies with the station; nothing is left running
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            out.close()
            tail = log_path.read_text(encoding='utf-8', errors='replace')[-1500:]
            job.close()
            raise ValueError('Remotion Studio exited during startup: ' + tail)
        if _http_ready(port):
            break
        time.sleep(.4)
    else:
        _kill(proc)
        job.close()
        raise ValueError(f'Remotion Studio did not answer within {timeout} s')
    elapsed = round(time.time() - started, 1)
    url = f"http://127.0.0.1:{port}/{m['composition_id']}"
    with _lock:
        _running[eid] = dict(proc=proc, job=job, port=port, url=url, started=now())
    state['startup_seconds'] = elapsed
    return dict(running=True, port=port, url=url, elapsed_seconds=elapsed, composition_id=m['composition_id'])
