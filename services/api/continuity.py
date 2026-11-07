"""Versioned continuity data and deterministic, independent Flow story-shot compiler.

No providers, subprocesses or writes here. Internal precision is NEVER interpolated
into art direction. Untranslatable input fails closed instead of being stripped.
"""
import hashlib
import io
import math
import json
import re
from pathlib import PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ENGINE = 'ODD_FRAME_VISUAL_CONTINUITY_V1'
VERSION = '1.0.0'


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)


class Property(Contract):
    key: str
    value: str


class Count(Contract):
    key: str
    value: int = Field(ge=0,strict=True)


def entries(value):
    return [dict(key=k,value=v) for k,v in value.items()] if isinstance(value,dict) else value


def mapping(value):
    result={entry.key:entry.value for entry in value}
    if len(result)!=len(value):raise ValueError('Duplicate continuity property key')
    return result


class Timeline(Contract):
    key: str
    value: list[Property]

    @field_validator('value',mode='before')
    @classmethod
    def normalize(cls,value):return entries(value)


class Reference(Contract):
    id: str
    category: Literal['character', 'turnaround', 'building', 'location', 'prop', 'style']
    path: str | None
    sha256: str | None
    approved: bool
    essential: bool

    @field_validator('path')
    @classmethod
    def public_path(cls,value):
        if value is not None:
            path=PureWindowsPath(value)
            if path.is_absolute() or path.drive or '..' in path.parts or any(p.casefold()=='.production' for p in path.parts):
                raise ValueError('References must use public episode-relative paths')
        return value


class Asset(Contract):
    id: str = Field(pattern=r'^(CHAR|BUILDING|PROP|LOC|STYLE)_[A-Z0-9_]+$')
    kind: Literal['character', 'building', 'prop', 'location', 'style']
    name: str
    description: str = Field(min_length=40)
    # Full exact specifications, including measurements, belong only here.
    specifications: list[Property]
    provenance: str = Field(min_length=5)
    design_status: Literal['approved', 'proposed']
    reference_ids: list[str]

    @field_validator('specifications',mode='before')
    @classmethod
    def normalize(cls,value):return entries(value)


class Relation(Contract):
    subject: str
    relation: Literal['above', 'below', 'left_of', 'right_of', 'upstream_of', 'near', 'taller_than']
    object: str
    evidence: str


class VisualBible(Contract):
    engine: Literal['ODD_FRAME_VISUAL_CONTINUITY_V1'] = ENGINE
    version: Literal['1.0.0'] = VERSION
    narration_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    assets: list[Asset] = Field(min_length=1,max_length=200)
    relationships: list[Relation] = Field(max_length=1000)
    geography: str = Field(min_length=30)
    palette_lighting: str = Field(min_length=20)
    references: list[Reference] = Field(max_length=500)


class Change(Contract):
    key: str
    before: str
    after: str
    narration_evidence: str = Field(min_length=3)
    evidence_source: Literal['narration', 'storyboard'] = 'narration'


class ScaleCheck(Contract):
    character_id: str
    building_id: str
    character_height: float = Field(gt=0)
    door_height: float = Field(gt=0)
    perspective: Literal['same_plane', 'separate_planes']
    character_plane: Literal['foreground', 'middle_ground', 'background']
    building_plane: Literal['foreground', 'middle_ground', 'background']
    composition: str = Field(min_length=20)


class Shot(Contract):
    scene_id: str = Field(pattern=r'^S\d{3}$')
    storyboard_sha256: str | None = Field(default=None,pattern=r'^[0-9a-f]{64}$')
    timeline: str  # present or a stable named flashback; each has its own state chain
    asset_ids: list[str]
    character_map: list[Property]  # existing C001 IDs -> canonical CHAR_* IDs
    moment: str = Field(min_length=20)
    expression_pose: str = Field(min_length=20)
    lighting: str = Field(min_length=20)
    composition: str = Field(min_length=20)
    geography: str = Field(min_length=20)
    visible_state: str = Field(min_length=20)
    state_keys: list[str] = Field(default_factory=list)
    state_assertions: list[Property] = Field(default_factory=list)
    prop_counts: list[Count] = Field(default_factory=list)
    changes: list[Change]
    scale_checks: list[ScaleCheck]

    @field_validator('character_map','prop_counts','state_assertions',mode='before')
    @classmethod
    def normalize(cls,value):return entries(value)


class Ledger(Contract):
    initial_states: list[Timeline]
    fixed_properties: list[Property]
    shots: list[Shot] = Field(min_length=1,max_length=100)

    @field_validator('initial_states','fixed_properties',mode='before')
    @classmethod
    def normalize(cls,value):return entries(value)


class ContinuityPlan(Contract):
    bible: VisualBible
    ledger: Ledger


# Only positive art direction is linted for diagram triggers. The fixed negative
# instructions necessarily name annotations to exclude them.
LEAKS = {
    'diagram language': r'\b(?:cross[- ]section|side elevation|technical elevation|engineering|survey drawing|scale drawing|diagram|coordinate table|measurement annotation|measurement arrows?|instructional arrows?|labeled marker|labelled marker|callouts?)\b',
    'internal identifier': r'\b(?:S\d{3}|C\d{3}|(?:CHAR|BUILDING|PROP|LOC)_[A-Z0-9_]+)\b',
    'technical measurement': r'(?<!\w)[+-]?\d+(?:\.\d+)?\s*(?:m|cm|mm|meters?|metres?|feet|ft|px)\b|\b(?:elevation|height|water)\s*[:=+]\s*\d',
    'coordinates': r'(?<!\w)\.?\d+\.?\d*\s*,\s*\.?\d+\.?\d*|\b[xyz]\s*[:=]\s*[+-]?\.?\d',
    'previous prompt dependency': r'\b(?:same (?:instant|moment|as|character|house|lodge|location|costume)|previous (?:scene|shot|prompt)|as before|as above|earlier prompt)\b',
    'placeholder': r'\b(?:TODO|TBD|PLACEHOLDER)\b|\{\{.*?\}\}|\[[A-Z_ ]{3,}\]',
    'annotation request': r'\b(?:label(?:ed|led)?\s+[A-Z](?:\b|/)|(?:stake|marker)\s+[A-C]\b|draw (?:an? )?arrow|annotat(?:e|ion)|caption (?:band|zone|area)|reserve.*caption)\b',
    'coordinate table': r'\|\s*(?:x|y|z|elevation)\s*\||\b(?:northing|easting)\b',
    'panel layout': r'\b(?:split[- ]screens?|split[- ]panels?|comic(?:[- ]style)? panels?|storyboard grid|diptych|triptych)\b',
}

STYLE = ('ODD FRAME: strictly hand-drawn cinematic illustrated 2D, clean dark ink outlines, expressive cartoon animals, '
         'layered scenery and controlled illustrated shading. Deep charcoal #14171C and muted slate #41464E '
         'dominate environmental materials; warm ivory #F1EBDD keeps faces and important features readable. '
         'Golden yellow #FFD43B guides attention to the primary story clue, with restrained pale yellow '
         '#FFF2B0 and muted ochre #A98428. Preserve approved local colors. Motivated genre-appropriate lighting; '
         'matte objects reflect light and never glow without a story-supported source.')
RESTRICTIONS = ('One cinematic 2D story illustration. Vertical 9:16 full-bleed artwork. '
                'No text or typography, no words, no letters or numbers, no measurements, no diagram arrows, '
                'no labels or explanatory callouts, no speech bubbles, no split panels or comic panels, '
                'no comic borders or decorative borders, no blank margins or empty caption areas, '
                'no logos or watermarks, no photorealism or 3D rendering, no unauthorized characters or limbs. '
                'Writing-bearing objects use blank surfaces or indistinct nonlinguistic texture. '
                'Static still image only; no generated video.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def storyboard_digest(scene):
    return digest({k:scene[k] for k in ('scene_id','narration_text','beat','character_ids','location','props',
        'expression_pose','focus','focus_reason','yellow_placement','lighting','framing','continuity')})


def lint(text):
    return [name for name, pattern in LEAKS.items() if re.search(pattern, text, re.I)]


def _reference(ref, root):
    result = {**ref.model_dump(), 'status': 'MISSING', 'attached': False}
    if not ref.path:
        return result
    # Same scoped path/link policy as all other production files.
    from .file_writer import EpisodeWriter
    path = EpisodeWriter(root).path(ref.path)
    if path.is_file() and ref.approved and ref.sha256:
        raw = path.read_bytes()
        result['status'] = 'AVAILABLE' if hashlib.sha256(raw).hexdigest() == ref.sha256 else 'HASH_MISMATCH'
        if result['status']=='AVAILABLE':
            from PIL import Image
            try:
                with Image.open(io.BytesIO(raw)) as decoded:
                    decoded.load()
                    if getattr(decoded,'n_frames',1)!=1:result['status']='INVALID_IMAGE'
            except (OSError,ValueError):result['status']='INVALID_IMAGE'
    elif path.is_file():
        result['status'] = 'UNAPPROVED'
    return result


def compile_plan(package, narration, episode_id, root):
    """Returns the unchanged v1 queue and sidecars; BLOCKED never yields jobs."""
    from .models import Flow
    from .skills import episode_art_direction,art_direction_receipt
    art=episode_art_direction(root)
    plan = ContinuityPlan.model_validate(package['visual_continuity'])
    bible, ledger = plan.bible, plan.ledger
    from .file_writer import EpisodeWriter
    registry_path=EpisodeWriter(root).path('02_characters/APPROVED_REFERENCES.json')
    registry=json.loads(registry_path.read_text(encoding='utf-8')) if registry_path.exists() else None
    issues = []
    def issue(level, message, scene_id=None):
        issues.append(dict(level=level, scene_id=scene_id, message=message))
    if art:
        for error in lint('\n'.join(art['profile'][k] for k in ('opening','style','material_policy'))):
            issue('BLOCKED','Cinematic profile leakage: '+error)
    assets = {a.id: a for a in bible.assets}
    refs = {r.id: r for r in bible.references}
    if registry:
        if registry.get('plan_sha256')!=digest(plan.model_dump()):
            issue('BLOCKED', 'Approved references belong to a different canonical plan')
        else:
            for record in registry['references']:
                pinned=Reference.model_validate(record)
                if pinned.id not in refs or pinned.category!=refs[pinned.id].category:
                    issue('BLOCKED', 'Approved reference has an undefined or conflicting assignment')
                else:refs[pinned.id]=pinned
    if len(assets) != len(bible.assets) or len(refs) != len(bible.references):
        issue('BLOCKED', 'Duplicate canonical asset or reference ID')
    if bible.narration_sha256 != hashlib.sha256(narration.encode()).hexdigest():
        issue('BLOCKED', 'Visual Bible does not match approved narration')
    words=lambda text:re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?",text.casefold().replace('’',"'"))
    if words(' '.join(s['narration_text'] for s in package['scenes'])) != words(narration):
        issue('BLOCKED', 'Storyboard does not cover approved narration exactly in order')
    for a in assets.values():
        if a.id.split('_')[0] != {'character':'CHAR','building':'BUILDING','location':'LOC','prop':'PROP','style':'STYLE'}[a.kind]:
            issue('BLOCKED', 'Asset identifier/kind mismatch: '+a.id)
        if set(a.reference_ids)-refs.keys():issue('BLOCKED', 'Undefined reference: '+a.id)
        for rid in a.reference_ids:
            allowed={'character':{'character','turnaround'},'building':{'building'},'location':{'location'},'prop':{'prop'},'style':{'style'}}[a.kind]
            if rid in refs and refs[rid].category not in allowed:issue('BLOCKED', 'Reference category contradicts asset assignment: '+a.id)
        if a.design_status == 'proposed':issue('WARNING', 'Proposed design with provenance: '+a.id)
    for rel in bible.relationships:
        if rel.subject not in assets or rel.object not in assets:issue('BLOCKED', 'Undefined geography/scale asset')
        inverse = {'above':'below', 'below':'above', 'left_of':'right_of', 'right_of':'left_of'}
        if any(r.subject == rel.subject and r.object == rel.object and r.relation == inverse.get(rel.relation) for r in bible.relationships):
            issue('BLOCKED', 'Contradictory fixed geographic relationships')
    # Detect impossible cycles as well as direct opposite relations.
    for relation in ('above','left_of','upstream_of','taller_than'):
        graph={}
        for rel in bible.relationships:
            subject,obj,kind=rel.subject,rel.object,rel.relation
            if kind=={'above':'below','left_of':'right_of'}.get(relation):subject,obj,kind=obj,subject,relation
            if kind==relation:graph.setdefault(subject,set()).add(obj)
        visited,visiting=set(),set()
        def cyclic(node):
            if node in visiting:return True
            if node in visited:return False
            visiting.add(node)
            if any(cyclic(child) for child in graph.get(node,())):return True
            visiting.remove(node);visited.add(node)
            return False
        if any(cyclic(node) for node in graph):issue('BLOCKED', 'Cyclic fixed relationship: '+relation)
    if [s.scene_id for s in ledger.shots] != [s['scene_id'] for s in package['scenes']]:
        issue('BLOCKED', 'Ledger/storyboard sequence mismatch')
    states = {k:mapping(v) for k,v in mapping(ledger.initial_states).items()}
    fixed_properties=mapping(ledger.fixed_properties)
    characters = {c['id']:c for c in package['characters']}
    jobs, scene_reports, ref_jobs = [], [], []
    heights={}
    for a in assets.values():
        specs=mapping(a.specifications)
        value=specs.get('height_units') if a.kind=='character' else specs.get('door_height_units') if a.kind=='building' else None
        if value is not None:
            try:
                height=float(value)
                if not math.isfinite(height) or height<=0:raise ValueError()
                heights[a.id]=height
            except ValueError:issue('BLOCKED', 'Invalid canonical relative height: '+a.id)
    for scene, shot in zip(package['scenes'], ledger.shots):
        sid = scene['scene_id']
        if shot.storyboard_sha256!=storyboard_digest(scene):issue('BLOCKED', 'Cinematic shot is bound to a different storyboard revision', sid)
        visible = set(shot.asset_ids)
        if len(visible) != len(shot.asset_ids) or visible-assets.keys():issue('BLOCKED', 'Duplicate or undefined visible asset', sid)
        character_map=mapping(shot.character_map)
        if len(set(scene['character_ids']))!=len(scene['character_ids']):issue('BLOCKED', 'Duplicate storyboard character assignment', sid)
        mapped = set(character_map.values())
        visible_chars = {a for a in visible if a in assets and assets[a].kind == 'character'}
        if set(character_map) != set(scene['character_ids']) or mapped != visible_chars or len(mapped)!=len(character_map):
            issue('BLOCKED', 'Visible character count or mapping contradicts storyboard', sid)
        for old, canonical in character_map.items():
            if old not in characters or canonical not in assets or characters[old]['description'] != assets[canonical].description:
                issue('BLOCKED', 'Canonical character description differs from approved package', sid)
        state = states.get(shot.timeline)
        if state is None:
            issue('BLOCKED', 'Undefined timeline initial state', sid); state = {}; states[shot.timeline] = state
        for change in shot.changes:
            if change.key in fixed_properties:issue('BLOCKED', 'Cannot mutate fixed world property: '+change.key, sid)
            if state.get(change.key) != change.before:issue('BLOCKED', 'Invalid state transition: '+change.key, sid)
            evidence_text=scene['narration_text'] if change.evidence_source=='narration' else ' '.join(scene[k] for k in ('beat','props','continuity'))
            if change.narration_evidence.casefold() not in evidence_text.casefold():
                issue('BLOCKED', 'State change lacks scene narration evidence: '+change.key, sid)
            state[change.key] = change.after
        for key,value in mapping(shot.state_assertions).items():
            if state.get(key)!=value:issue('BLOCKED', 'Scene state contradicts ledger: '+key, sid)
        for scale in shot.scale_checks:
            if scale.character_id not in visible_chars or scale.building_id not in visible or assets.get(scale.building_id, None) is None:
                issue('BLOCKED', 'Scale check references absent asset', sid)
            if scale.character_height > scale.door_height:
                issue('BLOCKED', 'Character exceeds door height; review canonical proportions', sid)
            if scale.perspective == 'same_plane' and scale.character_plane != scale.building_plane:
                issue('BLOCKED', 'Contradictory perspective planes', sid)
            for key,value in ((scale.character_id,scale.character_height),(scale.building_id,scale.door_height)):
                if key in heights and heights[key]!=value:issue('BLOCKED', 'Canonical scale changed between scenes: '+key, sid)
                heights[key]=value
        for rel in bible.relationships:
            if rel.relation=='taller_than' and rel.subject in heights and rel.object in heights and heights[rel.subject]<=heights[rel.object]:
                issue('BLOCKED', 'Relative character height contradicts canonical relationship', sid)
        prop_counts=mapping(shot.prop_counts)
        for aid in visible:
            if aid in assets and assets[aid].kind=='prop' and aid not in prop_counts:issue('BLOCKED', 'Missing visible prop inventory: '+aid, sid)
        for aid,count in prop_counts.items():
            if aid not in visible or aid not in assets or assets[aid].kind!='prop' or count<=0:
                issue('BLOCKED', 'Invalid visible prop count', sid);continue
            total=mapping(assets[aid].specifications).get('count')
            if total and total.isdigit() and count>int(total):issue('BLOCKED', 'Visible props exceed canonical inventory', sid)
        if visible_chars and any(assets[a].kind == 'building' for a in visible if a in assets) and not shot.scale_checks:
            issue('BLOCKED', 'Missing character-to-building scale checks', sid)
        if not re.search(r'\b(?:wide|medium|close|eye.level|low.angle|over.the.shoulder|full.body|establishing)\b',shot.composition,re.I):
            issue('BLOCKED', 'Missing cinematic shot framing', sid)
        descriptions = [assets[a].description for a in shot.asset_ids if a in assets]
        for key in shot.state_keys:
            if key not in state:issue('BLOCKED', 'Undefined visible state key: '+key, sid)
        positive = '\n'.join([shot.moment,shot.expression_pose,shot.lighting, f"Exactly {len(visible_chars)} visible {'character' if len(visible_chars)==1 else 'characters'}; no other characters.",
                              'Visible cast: '+(', '.join(characters[c]['name'] for c in character_map if c in characters) or 'none')+'.',
                              *descriptions, shot.composition, shot.geography, shot.visible_state,
                              *(state[k] for k in shot.state_keys if k in state),
                              *(s.composition for s in shot.scale_checks), bible.palette_lighting])
        if prop_counts:
            positive+='\nVisible recurring prop inventory: '+', '.join(str(count)+' '+assets[aid].name for aid,count in prop_counts.items() if aid in assets)+'.'
        positive+='\nOnly the scene inventory is present; optional possessions mentioned in identity descriptions are absent unless explicitly included in this moment.'
        if re.search(r'\bfull[- ]body\b',shot.composition,re.I):
            positive+='\nKeep the entire head, feet and any natural tail inside the frame with comfortable margins.'
        for error in lint(positive):issue('BLOCKED', 'Art-direction leakage: '+error, sid)
        if art:
            profile=art['profile']
            focus='The eye is drawn to '+scene['focus']+'. '+scene['yellow_placement']
            for error in lint(focus):issue('BLOCKED','Art-direction leakage: '+error,sid)
            count=f"Exactly {len(visible_chars)} visible {'character' if len(visible_chars)==1 else 'characters'}; no other characters."
            char_descriptions=[assets[a].description for a in shot.asset_ids if a in visible_chars]
            other_descriptions=[assets[a].description for a in shot.asset_ids if a in assets and a not in visible_chars]
            framing=[shot.composition,*(s.composition for s in shot.scale_checks),focus]
            if re.search(r'\bfull[- ]body\b',shot.composition,re.I):framing.append('Keep the entire head, feet and any natural tail inside the frame with comfortable margins.')
            inventory='Visible recurring prop inventory: '+', '.join(str(count)+' '+assets[aid].name for aid,count in prop_counts.items() if aid in assets)+'.' if prop_counts else 'No additional recurring props are visible.'
            prompt='\n'.join([profile['opening'],shot.moment,shot.expression_pose,count,
                'Visible cast: '+(', '.join(characters[c]['name'] for c in character_map if c in characters) or 'none')+'.',
                *char_descriptions,*other_descriptions,shot.geography,*framing,
                profile['style'],profile['material_policy'],bible.palette_lighting,shot.lighting,
                shot.visible_state,*(state[k] for k in shot.state_keys if k in state),inventory,
                'Only the scene inventory is present; optional possessions mentioned in identity descriptions are absent unless explicitly included in this moment.',profile['exclusions']])
        else:prompt = positive+'\n'+STYLE+'\n'+RESTRICTIONS
        if len(prompt.encode()) > 24000:issue('BLOCKED', 'Prompt exceeds 24000-byte compiler budget; nothing truncated', sid)
        required = sorted({r for a in visible if a in assets for r in assets[a].reference_ids} |
                          {r.id for r in bible.references if r.category == 'style'})
        requirements = []
        for rid in required:
            if rid not in refs:continue
            try:record = _reference(refs[rid], root)
            except (ValueError, OSError):
                record = {**refs[rid].model_dump(), 'status':'UNSAFE_OR_UNREADABLE', 'attached':False}
            requirements.append(record)
            if record['status'] != 'AVAILABLE':
                blocking=refs[rid].essential or refs[rid].approved or record['status'] in ('HASH_MISMATCH','UNSAFE_OR_UNREADABLE','INVALID_IMAGE')
                issue('BLOCKED' if blocking else 'WARNING', 'Reference '+rid+': '+record['status'], sid)
        ref_jobs.append(dict(scene_id=sid, references=requirements, attached=False))
        scene_reports.append(dict(scene_id=sid, timeline=shot.timeline, state=dict(state),
                                  character_count=len(visible_chars), asset_ids=shot.asset_ids,
                                  prompt_characters=len(prompt), prompt_utf8_bytes=len(prompt.encode()),
                                  prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                                  scale_checks=[s.model_dump() for s in shot.scale_checks]))
        jobs.append(dict(job_id=sid+'_IMG',scene_id=sid,type='image',prompt=prompt,source_image=None,output_name=sid))
    status = 'BLOCKED' if any(i['level']=='BLOCKED' for i in issues) else 'WARNING' if issues else 'PASS'
    if art:
        if status=='WARNING':status='REVIEW'
        for finding in issues:
            if finding['level']=='WARNING':finding['level']='REVIEW'
    report = dict(engine=ENGINE,version=VERSION,status=status,issues=issues,scenes=scene_reports,
                  plan_sha256=digest(plan.model_dump()), visual_inspection='NOT_PERFORMED',
                  semantic_validation='NOT_PERFORMED', queue_schema='1.0')
    manifest = dict(engine=ENGINE, version=VERSION, jobs=ref_jobs, attachment_capability='UNVERIFIED',
                    note='No attachment is claimed. source_image remains null; verify the extension before attaching references.')
    generation_manifest=None
    if art:
        receipt=art_direction_receipt(art)
        report['visual_art_direction']=receipt
        manifest['visual_art_direction']=receipt
        generation_manifest=dict(skill=receipt,visual_bible_version=bible.version,visual_bible_sha256=digest(bible.model_dump()),
            plan_sha256=digest(plan.model_dump()),queue_schema_version='1.0',prompt_validation=status,
            visual_validation='NOT_PERFORMED',queue_readiness='BLOCKED' if status=='BLOCKED' else 'REVIEW' if status=='REVIEW' else 'PROMPT_VALIDATED',
            shots=[dict(scene_id=s.scene_id,moment=s.moment,composition=s.composition) for s in ledger.shots],
            prompts=[dict(scene_id=s['scene_id'],sha256=s['prompt_sha256'],characters=s['prompt_characters'],utf8_bytes=s['prompt_utf8_bytes']) for s in scene_reports])
    return dict(flow=None if status=='BLOCKED' else Flow(episode_id=episode_id,jobs=jobs).model_dump(),
                report=report, references=manifest, bible=bible.model_dump(), ledger=ledger.model_dump(),generation_manifest=generation_manifest)


def legacy_prompt(scene, chars):
    """Compatibility path: preserve exact descriptors, reject unsafe raw planning text."""
    descriptions = '\n'.join(chars[c]['name']+': '+chars[c]['description'] for c in scene['character_ids'])
    positive = '\n'.join([scene[k] for k in ('beat','expression_pose','location','props','framing','focus','yellow_placement','lighting','continuity')])
    problems = lint(positive+'\n'+descriptions)
    if problems:
        raise ValueError('Cinematic prompt BLOCKED for '+scene['scene_id']+': '+', '.join(problems)+
                         '. Supply a versioned cinematic continuity plan; internal details were not silently stripped.')
    return positive+'\nExactly '+str(len(scene['character_ids']))+' visible characters.\n'+descriptions+'\n'+STYLE+'\n'+RESTRICTIONS
