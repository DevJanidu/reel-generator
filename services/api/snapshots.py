"""Controller-only immutable creative/template/music inputs for an episode or idea session."""
import json
import os
import re
from pathlib import Path
from .core import ROOT,now,sha,read_json
from .file_writer import EpisodeWriter,no_links
from .skills import load_skills

def bootstrap(root,source_root=ROOT):
    if os.getenv('ODD_EPISODE_WORKER')=='1':raise ValueError('Production workers cannot bootstrap or replace immutable inputs')
    root=Path(root);writer=EpisodeWriter(root)
    if (root/'.production/provenance.json').exists():return validate(root)
    docs,rules=load_skills(source_root)
    files=['brand/SKILLS_MANIFEST.json','brand/ODD_FRAME_RULES.json',*[d['canonical_path'] for d in docs]]
    if (source_root/'brand/EDITING_PROFILES.json').is_file():files.append('brand/EDITING_PROFILES.json')
    files += ['prompts/'+p.name for p in (source_root/'prompts').glob('*.md')]
    records=[]
    for relative in files:
        source=source_root/relative;no_links(source);raw=source.read_bytes()
        writer.bytes('.production/input_snapshot/'+relative,raw,immutable=True)
        records.append(dict(source=str(source),path=relative,sha256=sha(raw),byte_length=len(raw)))
    for source,relative in [(ROOT/'video/remotion/src/index.tsx','remotion/src/index.tsx'),(ROOT/'video/remotion/src/composition.tsx','remotion/src/composition.tsx'),(ROOT/'video/remotion/render.mjs','remotion/render.mjs'),(ROOT/'package-lock.json','runtime/package-lock.json')]:
        raw=source.read_bytes();writer.bytes('.production/input_snapshot/'+relative,raw,immutable=True)
        records.append(dict(source=str(source),path=relative,sha256=sha(raw),byte_length=len(raw)))
    runtime_manifest=ROOT/'video/remotion/runtime-binaries/manifest.json'
    media_runtime=None
    if runtime_manifest.exists():
        raw=runtime_manifest.read_bytes()
        writer.bytes('.production/input_snapshot/runtime/media-manifest.json',raw,immutable=True)
        records.append(dict(source=str(runtime_manifest),path='runtime/media-manifest.json',sha256=sha(raw),byte_length=len(raw)))
        media_runtime=dict(directory=str(runtime_manifest.parent),manifest=read_json(runtime_manifest))
    music=dict(status='NOT_SUPPLIED',version=None,sha256=None,rights_evidence='')
    configured=os.getenv('ODD_SIGNATURE_MUSIC','')
    if configured:
        source=Path(configured).absolute();no_links(source)
        if not source.is_file():raise ValueError('Configured signature instrumental is missing: '+str(source))
        relative='media/signature'+source.suffix.lower();raw=source.read_bytes()
        writer.bytes('.production/input_snapshot/'+relative,raw,immutable=True)
        records.append(dict(source=str(source),path=relative,sha256=sha(raw),byte_length=len(raw)))
        music=dict(status='PINNED',version=os.getenv('ODD_SIGNATURE_MUSIC_VERSION','1'),sha256=sha(raw),path=relative,rights_evidence=os.getenv('ODD_SIGNATURE_MUSIC_RIGHTS',''))
        writer.bytes('05_assets/music/signature'+source.suffix.lower(),raw,replace=False)
    provenance=dict(version='2.0',created=now(),files=records,skill_versions={d['id']:d['version'] for d in docs},
                    master_prompt_version=re.search(r'^Version:\s*([0-9.]+)',(source_root/'prompts/00_MASTER_PROMPT.md').read_text(encoding='utf-8'),re.M).group(1),remotion_template_version=read_json(ROOT/'video/remotion/package.json')['dependencies']['remotion'],signature_music=music,media_runtime=media_runtime)
    writer.json('.production/provenance.json',provenance,immutable=True)
    return provenance

def validate(root,media=False):
    root=Path(root);no_links(root)
    snapshot=root/'.production/input_snapshot';provenance=read_json(root/'.production/provenance.json')
    for record in provenance['files']:
        path=snapshot/record['path'];no_links(path);raw=path.read_bytes()
        if len(raw)!=record['byte_length'] or sha(raw)!=record['sha256']:raise ValueError('Pinned episode input was changed: '+record['path'])
    load_skills(snapshot)
    if media:
        runtime=provenance.get('media_runtime')
        if not runtime:raise ValueError('Pinned media runtime is unavailable. Run scripts/setup.ps1 in development mode before creating this episode.')
        for item in runtime['manifest']['files']:
            path=Path(runtime['directory'])/item['path'];no_links(path)
            if sha(path.read_bytes())!=item['sha256']:raise ValueError('Shared native media runtime changed; refusing to silently alter pinned episode dependencies')
    return provenance

def source_root(root):
    validate(root)
    return Path(root)/'.production/input_snapshot'

def pin_imported_music(root,path,rights=None):
    if os.getenv('ODD_EPISODE_WORKER')=='1':raise ValueError('Workers cannot modify immutable music inputs')
    root=Path(root);path=Path(path);writer=EpisodeWriter(root);provenance=validate(root)
    raw=path.read_bytes();digest=sha(raw)
    current=provenance['signature_music']
    if current['status']=='PINNED':
        if current['sha256']!=digest:raise ValueError('This episode is pinned to a different instrumental. Create a new episode to change signature music.')
        return current
    relative='media/signature'+path.suffix.lower()
    writer.bytes('.production/input_snapshot/'+relative,raw,immutable=True)
    provenance['files'].append(dict(source='Owner-imported episode instrumental',path=relative,sha256=digest,byte_length=len(raw)))
    provenance['signature_music']=dict(status='PINNED',version='owner-import-1',sha256=digest,path=relative,rights_evidence=rights or '')
    # Explicit trusted import completes a previously missing input; never replaces a pinned value.
    from .file_writer import parent_handles
    destination=root/'.production/provenance.json'
    with parent_handles(destination):
        temporary=destination.with_suffix('.pending')
        temporary.write_text(json.dumps(provenance,indent=2),encoding='utf-8');temporary.replace(destination)
    return provenance['signature_music']
