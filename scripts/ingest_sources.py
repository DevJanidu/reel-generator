"""Explicit source ingestion. Never run automatically on application startup."""
from pathlib import Path
import hashlib
import json
import re
import os
if os.getenv('ODD_EPISODE_WORKER')=='1':raise SystemExit('Source ingestion is a development-only operation')

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('ODD_FRAME_OFFICIAL_CONTENT_BIBLE_v1.md', 'references/ODD_FRAME_OFFICIAL_CONTENT_BIBLE_v1.md', '1.0', 'Brand authority and story identity', 'OFFICIAL CONTENT BIBLE'),
    ('ODD_FRAME_FANBASE_GROWTH_PSYCHOLOGY_SKILL.md', 'skills/ODD_FRAME_FANBASE_GROWTH_PSYCHOLOGY_SKILL.md', '1.0.0', 'Attention, curiosity, emotion, sharing and loyalty', 'FANBASE & REELS GROWTH'),
    ('OddFrame Design.md', 'skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md', '1.0', 'Midnight Gold still-image art direction and continuity', '2D Still Graphic Design Guide'),
    ('ODD_FRAME_TYPOGRAPHY_AND_MOTION_GUIDE.md', 'skills/ODD_FRAME_TYPOGRAPHY_AND_MOTION_GUIDE.md', '1.0', 'Typography, readability and frame-based text motion', 'Typography and Motion Guide'),
]

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    entries = []
    for index, (name, canonical, version, role, signature) in enumerate(SOURCES):
        source = ROOT / name
        raw = source.read_bytes()
        content = raw.decode('utf-8-sig')
        if signature not in content or len(content) < 1000:
            raise ValueError(f'Incorrect or incomplete source: {source}')
        original = ROOT / 'source_documents' / name
        original.parent.mkdir(parents=True, exist_ok=True)
        if original.exists() and original.read_bytes() != raw:
            raise ValueError(f'Refusing to overwrite different original: {original}')
        original.write_bytes(raw)
        normalized = content
        if index == 2:
            normalized = normalized.replace('Say It Better', 'ODD FRAME').replace('say-it-better', 'odd-frame')
        target = ROOT / 'brand' / canonical
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = normalized.encode('utf-8')
        if target.exists() and target.read_bytes() != encoded:
            raise ValueError(f'Review differences before overwriting {target}')
        target.write_bytes(encoded)
        entries.append(dict(id=['bible','psychology','design','typography'][index], canonical_path='brand/'+canonical,
                            source_path=name, preserved_source_path='source_documents/'+name,
                            source_version=version, version=version, sha256=digest(encoded),
                            source_sha256=digest(raw), byte_length=len(encoded), mandatory=True,
                            reading_order=index+1, precedence=index+2, responsibility=role,
                            signature=signature, known_conflicts=(['Say It Better renamed to ODD FRAME'] if index == 2 else
                                ['Older optional captions, image movement and SFX are overridden by ODD_FRAME_RULES.json'])))
    manifest = dict(schema_version='1.0', brand='ODD FRAME', override_version='1.1.0',
                    rules_sha256=digest((ROOT/'brand/ODD_FRAME_RULES.json').read_bytes()),
                    editing_profiles_sha256=digest((ROOT/'brand/EDITING_PROFILES.json').read_bytes()), documents=entries)
    (ROOT/'brand/SKILLS_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('Preserved four originals and normalized all four full documents.')

if __name__ == '__main__':
    main()
