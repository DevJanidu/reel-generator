"""Complete read, pinned digest, explicit context bound: no creative bypass."""
import json
import re
from .core import ROOT, now, sha, read_json

IDS = ['bible','psychology','design','typography']
PATHS = ['brand/references/ODD_FRAME_OFFICIAL_CONTENT_BIBLE_v1.md',
         'brand/skills/ODD_FRAME_FANBASE_GROWTH_PSYCHOLOGY_SKILL.md',
         'brand/skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md',
         'brand/skills/ODD_FRAME_TYPOGRAPHY_AND_MOTION_GUIDE.md']

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
    return loaded, rules

def skill_status(root=ROOT):
    at = now()
    try:
        docs,rules = load_skills(root)
        return dict(valid=True, checked_at=at, override_version=rules['version'], documents=[{k:v for k,v in d.items() if k!='text'} for d in docs])
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
    master=(root/'prompts/00_MASTER_PROMPT.md').read_text(encoding='utf-8')
    stage=(root/'prompts'/task).read_text(encoding='utf-8')
    if not master.strip() or not stage.strip():
        raise ValueError('Master or task prompt is empty')
    full='\n\n'.join(f'=== FULL AUTHORITATIVE DOCUMENT {d["reading_order"]}: {d["canonical_path"]} ===\n{d["text"]}\n=== END FULL DOCUMENT ===' for d in docs)
    system=full+'\n\n=== MASTER PROMPT ===\n'+master+'\n\n=== CURRENT OVERRIDES: HIGHEST AUTHORITY ===\n'+json.dumps(rules,ensure_ascii=False)+'\n\n=== TASK ===\n'+stage
    messages=[dict(role='system',content=system),dict(role='user',content=json.dumps(payload,ensure_ascii=False))]
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
    return messages,evidence
