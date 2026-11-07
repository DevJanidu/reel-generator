"""Complete read, pinned digest, explicit context bound: no creative bypass."""
import json
import re
from .core import ROOT, now, sha, read_json

IDS = ['bible','psychology','design','typography']
PATHS = ['brand/references/ODD_FRAME_OFFICIAL_CONTENT_BIBLE_v1.md',
         'brand/skills/ODD_FRAME_FANBASE_GROWTH_PSYCHOLOGY_SKILL.md',
         'brand/skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md',
         'brand/skills/ODD_FRAME_TYPOGRAPHY_AND_MOTION_GUIDE.md']

ART_ID='odd-frame-cinematic-2d-still-art-direction'
ART_VERSION='3.0.0'
ART_PATH='brand/skills/'+ART_ID+'/SKILL.md'
ART_PROFILE_PATH='brand/skills/'+ART_ID+'/ART_DIRECTION.json'


def validate_art_direction(record,root=ROOT):
    """Read the COMPLETE canonical candidate/approved skill and its pinned compiler data."""
    from .file_writer import no_links
    if (record.get('id')!=ART_ID or record.get('version')!=ART_VERSION or
        record.get('canonical_path')!=ART_PATH or record.get('profile_path')!=ART_PROFILE_PATH):
        raise ValueError('Cinematic art-direction registration has an unsupported identity, version or path')
    path=root/ART_PATH;no_links(path)
    try:raw=path.read_bytes();text=raw.decode('utf-8',errors='strict')
    except (OSError,UnicodeError) as exc:raise ValueError('Cinematic art-direction skill is missing or unreadable; restore the pinned full skill before image prompts') from exc
    if not text.strip() or len(raw)!=record.get('byte_length') or sha(raw)!=record.get('sha256'):
        raise ValueError('Cinematic art-direction skill is empty, truncated or changed; no fallback to old prompts')
    if ('# ODD FRAME — Cinematic Hand-Drawn 2D Story Still Skill v3.0' not in text or
        not re.search(r'^Version:\s*3\.0\.0\s*$',text,re.M)):
        raise ValueError('Cinematic art-direction source signature/version disagrees with registration')
    profile_path=root/ART_PROFILE_PATH;no_links(profile_path)
    try:profile_raw=profile_path.read_bytes();profile=json.loads(profile_raw)
    except (OSError,ValueError) as exc:raise ValueError('Pinned cinematic compiler profile is missing or unreadable') from exc
    if sha(profile_raw)!=record.get('profile_sha256') or len(profile_raw)!=record.get('profile_byte_length'):
        raise ValueError('Pinned cinematic compiler profile changed; no fallback to old prompts')
    if (profile.get('profile_id')!=ART_ID or profile.get('skill_version')!=ART_VERSION or
        set(profile)!={'profile_id','skill_version','opening','style','material_policy','exclusions'} or
        any(not isinstance(profile.get(k),str) or not profile[k].strip() for k in profile)):
        raise ValueError('Invalid cinematic compiler profile')
    return dict(**record,text=text,profile=profile,loaded_at=now(),full_read_validated=True)


def load_art_direction(root=ROOT,required=False):
    registry=read_json(root/'brand/SKILLS_MANIFEST.json').get('visual_art_direction',{})
    approved=registry.get('approved')
    if not approved:
        if required or registry.get('required'):
            raise ValueError('Cinematic art direction v3 is not approved/enabled in these pinned inputs. Owner approval is required; no new-style queue can be marked ready.')
        return None
    if approved.get('status')!='approved' or not approved.get('approved_at') or not approved.get('approved_by'):
        raise ValueError('Cinematic art-direction approval receipt is incomplete')
    return validate_art_direction(approved,root)


def art_direction_receipt(loaded):
    return {k:v for k,v in loaded.items() if k not in ('text','profile')} if loaded else None


def compact_schema_annotations(value):
    """Remove display-only JSON Schema titles; preserve all validation constraints."""
    if isinstance(value,dict):
        result={}
        for k,v in value.items():
            if k=='title':continue
            if k in ('properties','$defs','definitions','patternProperties','dependentSchemas') and isinstance(v,dict):
                result[k]={name:compact_schema_annotations(schema) for name,schema in v.items()}
            else:result[k]=compact_schema_annotations(v)
        return result
    if isinstance(value,list):return [compact_schema_annotations(v) for v in value]
    return value


def episode_art_direction(root):
    """Every compilation/regeneration rereads full immutable instructions, never global defaults."""
    from pathlib import Path
    from . import snapshots
    root=Path(root)
    if not (root/'.production/provenance.json').exists():
        if (root/'episode.json').exists() or (root/'.production').exists():
            raise ValueError('Pinned episode inputs are missing; cannot fall back to legacy art direction')
        return None
    source=snapshots.source_root(root)
    return load_art_direction(source)

def load_skills(root=ROOT):
    manifest = read_json(root/'brand/SKILLS_MANIFEST.json')
    docs = manifest['documents']
    if manifest.get('brand') != 'ODD FRAME' or [d['id'] for d in docs] != IDS:
        raise ValueError('Manifest must register exactly four ordered ODD FRAME documents')
    loaded = []
    for index,d in enumerate(docs):
        if d['canonical_path'] != PATHS[index] or not d['mandatory'] or d['reading_order'] != index+1:
            raise ValueError('Invalid mandatory document path or order')
        path = root / d['canonical_path']
        # read_bytes returns complete content or fails. Size AND hash detect partial/truncated loads.
        raw = path.read_bytes()
        text = raw.decode('utf-8', errors='strict')
        if not text.strip() or len(raw) != d['byte_length'] or sha(raw) != d['sha256']:
            raise ValueError(f'Missing, empty, truncated or changed skill: {d["canonical_path"]}. Review changes and explicitly update manifest.')
        if d['signature'] not in text or not d.get('version'):
            raise ValueError(f'Wrong source signature/version: {path}')
        version_match=re.search(r'(?:^version:\s*|\*\*Version:\*\*\s*)([0-9.]+)',text,re.M)
        if not version_match or version_match.group(1).rstrip('.')!=d['version'] or d['source_version']!=d['version']:
            raise ValueError(f'Source text/version manifest disagreement: {path}')
        if index == 2 and 'say it better' in text.lower():
            raise ValueError('Canonical design skill still uses obsolete branding')
        loaded.append(dict(**d, text=text, found=True, status='LOADED', validated_at=now(), actual_sha256=sha(raw)))
    rules = read_json(root/'brand/ODD_FRAME_RULES.json')
    if rules['version'] != manifest['override_version']:
        raise ValueError('Manifest/rules version mismatch')
    if manifest.get('rules_sha256') != sha((root/'brand/ODD_FRAME_RULES.json').read_bytes()):
        raise ValueError('Production overrides changed without a reviewed manifest update')
    if rules['visuals'].get('transition') not in ('cut','profile_defined'):
        raise ValueError('Configuration contradicts the approved ODD FRAME production policy (transition)')
    profiles_hash=manifest.get('editing_profiles_sha256')
    taxonomy_hash=manifest.get('genre_taxonomy_sha256')
    if taxonomy_hash:
        from . import genres
        if sha((root/genres.PATH).read_bytes())!=taxonomy_hash:raise ValueError('Story taxonomy changed without a reviewed manifest update')
        genres.load(root)
    if profiles_hash:
        profiles_path=root/'brand/EDITING_PROFILES.json'
        if sha(profiles_path.read_bytes())!=profiles_hash:
            raise ValueError('Editing profiles changed without a reviewed manifest update')
        from .styles import validate_profiles
        validate_profiles(read_json(profiles_path))
    if (rules['visuals']['type']!='image' or rules['visuals']['image_motion']!='static' or
        rules['visuals']['generated_video'] or not rules['captions']['required'] or rules['audio']['sfx'] or
        rules['audio']['sources']!=['narration','instrumental'] or rules['output']!={'width':1080,'height':1920,'fps':30,'video_codec':'h264','audio_codec':'aac'}):
        raise ValueError('Configuration contradicts the approved ODD FRAME production policy')
    from .storytelling import load_extension
    extension = load_extension(root)
    master_path = root/'prompts/00_MASTER_PROMPT.md'
    if master_path.exists() and re.search(r'^Version:\s*3\.1\.', master_path.read_text(encoding='utf-8'), re.M) and not extension:
        raise ValueError('Version 3.1 master requires its registered storytelling extension')
    return loaded, rules

def skill_status(root=ROOT):
    at = now()
    try:
        docs,rules = load_skills(root)
        registry=read_json(root/'brand/SKILLS_MANIFEST.json').get('visual_art_direction',{})
        art=load_art_direction(root)
        return dict(valid=True, checked_at=at, override_version=rules['version'], documents=[{k:v for k,v in d.items() if k!='text'} for d in docs],
                    visual_art_direction=art_direction_receipt(art) or dict(status='ready-for-owner-approval' if registry.get('candidate') else 'LEGACY_PINNED',active=False))
    except (OSError,ValueError,KeyError,UnicodeError) as e:
        rows=[]
        try:
            for d in read_json(root/'brand/SKILLS_MANIFEST.json')['documents']:
                p=root/d['canonical_path']
                try:
                    raw=p.read_bytes()
                    valid=len(raw)==d['byte_length'] and sha(raw)==d['sha256'] and bool(raw.strip())
                    rows.append(dict(**d,found=True,status='LOADED' if valid else 'FAILED',actual_sha256=sha(raw),validated_at=at))
                except OSError:
                    rows.append(dict(**d,found=False,status='MISSING',validated_at=at))
        except (OSError,ValueError,KeyError):
            pass
        return dict(valid=False, checked_at=at, error=str(e), documents=rows)

def model_request(task, payload, config, root=ROOT):
    docs,rules=load_skills(root)
    art=load_art_direction(root)
    master=(root/'prompts/00_MASTER_PROMPT.md').read_text(encoding='utf-8')
    stage=(root/'prompts'/task).read_text(encoding='utf-8')
    if not master.strip() or not stage.strip():
        raise ValueError('Master or task prompt is empty')
    full='\n\n'.join(f'=== FULL AUTHORITATIVE DOCUMENT {d["reading_order"]}: {d["canonical_path"]} ===\n{d["text"]}\n=== END FULL DOCUMENT ===' for d in docs)
    taxonomy=None
    if (root/'brand/STORY_GENRES.json').exists():
        from . import genres
        taxonomy=genres.load(root)
    system=full+'\n\n=== MASTER PROMPT ===\n'+master+'\n\n=== CURRENT OVERRIDES: HIGHEST AUTHORITY ===\n'+json.dumps(rules,ensure_ascii=False)
    if taxonomy is not None:system+='\n\n=== COMPLETE PINNED STORY GENRE TAXONOMY ===\n'+json.dumps(taxonomy,ensure_ascii=False)
    from .storytelling import load_extension
    extension = load_extension(root)
    if extension:
        system+='\n\n=== COMPLETE PINNED STORYTELLING EXTENSION: RETENTION FIRST, HUMAN MIRROR OPTIONAL ===\n'+extension['text']+'\n'+json.dumps(extension['policy'],ensure_ascii=False)
    system+='\n\n=== TASK ===\n'+stage
    if art:
        system+='\n\n=== COMPLETE APPROVED CINEMATIC ART DIRECTION v3: VISUAL-STYLE AUTHORITY ===\n'+art['text']
        system+='\nManifest approval is authoritative for this exact source checksum; its proposal label is retained for provenance. V3 supersedes older visual style only. Preserve episode canon, floors, geography, narration, production overrides and isolation. Its OF_R002 example is not story input for other episodes.'
    messages=[dict(role='system',content=system),dict(role='user',content=json.dumps(payload,ensure_ascii=False,separators=(',',':')))]
    # One UTF-8 byte per token is deliberately conservative, including task input/output reserve.
    bound=sum(len(m['content'].encode('utf-8')) for m in messages)+config['output_tokens']+512
    if bound > config['context_tokens']:
        raise ValueError(f'Full instructions need conservative context bound {bound}; configured {config["context_tokens"]}. Increase context or choose another model. Nothing was truncated.')
    master_version=re.search(r'^Version:\s*([0-9.]+)',master,re.M)
    if not master_version:raise ValueError('Master prompt version is missing')
    evidence=dict(brand='ODD FRAME',timestamp=now(),provider=config['provider'],model=config['model'] or ('Installed CLI default' if config['provider'].endswith('_cli') else 'External manual model (not independently observed)'),
                  master_prompt=dict(path='prompts/00_MASTER_PROMPT.md',version=master_version.group(1),sha256=sha(master)),
                  skills=[{k:v for k,v in d.items() if k!='text'} for d in docs],
                  override_version=rules['version'],override_sha256=sha(json.dumps(rules,sort_keys=True)),
                  task=task, stage_prompt_sha256=sha(stage), full_read_validated=True, context_byte_upper_bound=bound,
                  request_sha256=sha(json.dumps(messages,ensure_ascii=False)))
    if art:evidence['visual_art_direction']=art_direction_receipt(art)
    if taxonomy is not None:evidence['genre_taxonomy']=dict(version=taxonomy['version'],sha256=sha((root/'brand/STORY_GENRES.json').read_bytes()))
    if extension:evidence['storytelling_extension']=extension['provenance']
    return messages,evidence
