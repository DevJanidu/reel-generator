"""Versioned craft guidance and editorial evidence, never a retention predictor."""
import json, math
from .core import read_json, sha
from .storytelling_models import HumanMirror, RetentionAudit, RetentionPlan, VoiceCalibration

EXTENSION = 'brand/storytelling/ODD_FRAME_STORYTELLING_V3_1.md'
POLICY = 'brand/storytelling/POLICY_V3_1.json'

def load_extension(root):
    manifest = read_json(root/'brand/SKILLS_MANIFEST.json')
    entry = manifest.get('storytelling_extension')
    if not entry:
        return None  # Historical snapshots have no extension and keep their old behavior.
    if entry.get('path') != EXTENSION or entry.get('policy_path') != POLICY or entry.get('version') != '3.1.0':
        raise ValueError('Unsupported storytelling extension registration')
    raw = (root/EXTENSION).read_bytes(); policy_raw = (root/POLICY).read_bytes()
    if len(raw) != entry['byte_length'] or sha(raw) != entry['sha256'] or sha(policy_raw) != entry['policy_sha256']:
        raise ValueError('Storytelling extension changed without a reviewed manifest update')
    text = raw.decode('utf-8'); policy = json.loads(policy_raw)
    if 'Version: 3.1.0' not in text or policy.get('version') != entry['version']:
        raise ValueError('Storytelling extension version mismatch')
    if policy.get('priority')!='ODD_FRAME_RETENTION_FIRST_V1' or policy.get('human_mirror')!='ODD_FRAME_HUMAN_MIRROR_V1' or policy.get('duration_is_hard_limit') is not False or policy.get('extra_approval_gates')!=0:
        raise ValueError('Storytelling policy contradicts the approved combined framework')
    return dict(text=text, policy=policy, provenance={k:v for k,v in entry.items() if k != 'text'})

def planning_context(root, payload):
    extension = load_extension(root)
    if not extension:
        return None
    selection = payload.get('genre_context') or payload
    preference = selection.get('human_mirror_preference', 'automatic')
    calibration = selection.get('voice_calibration')
    timing = dict(preferred_seconds=[40,55], strict_limit=False, measured_voice_wpm=None,
                  word_budget=None, basis='No measured voice evidence supplied; duration remains provisional')
    if calibration:
        measured = VoiceCalibration.model_validate(calibration)
        wpm = measured.measured_words / measured.measured_seconds * 60
        timing.update(measured_voice_wpm=round(wpm,2), word_budget=[math.floor(wpm*40/60), math.ceil(wpm*55/60)],
                      basis='Owner-supplied measured delivery sample, not independent verification',
                      calibration=measured.model_dump())
    return dict(version='3.1.0', priority='ODD_FRAME_RETENTION_FIRST_V1',
                human_mirror_system='ODD_FRAME_HUMAN_MIRROR_V1', human_mirror_preference=preference,
                timing=timing, note='Editorial guidance, not a performance prediction; genre and story needs take precedence')

def validate_analysis(root, task, data, payload):
    if not load_extension(root):
        return
    preference = (payload.get('genre_context') or payload).get('human_mirror_preference', 'automatic')
    items = data['ideas'] if task == 'genre_ideas' else [data] if task in ('script','review') else []
    for item in items:
        if not item.get('human_mirror'):
            raise ValueError('This pinned storytelling version requires Human Mirror analysis, including valid pure entertainment')
        mirror = HumanMirror.model_validate(item['human_mirror'])
        if preference == 'pure_entertainment' and (mirror.mode != 'none' or mirror.reflective_ending_recommended):
            raise ValueError('Pure entertainment preference cannot be replaced with a human-message ending')
        if task == 'genre_ideas':
            if not item.get('retention_plan'):raise ValueError('A concise retention plan is required for each new concept')
            RetentionPlan.model_validate(item['retention_plan'])
        if task in ('script','review'):
            if not item.get('retention_audit'):raise ValueError('New scripts require a promise, progression and ten-domain logic audit')
            RetentionAudit.model_validate(item['retention_audit'])

def approved_context(script, narration, preference='automatic'):
    if not script.get('human_mirror') and not script.get('retention_audit'):
        return None
    current = script.get('_review_narration_sha256') == sha(narration)
    return dict(version='3.1.0', human_mirror_preference=preference, human_mirror=script.get('human_mirror'),
                retention_audit=script.get('retention_audit'), review_matches_approved_wording=current,
                voice_timing=script.get('_voice_timing'),
                reviewed_narration_sha256=script.get('_review_narration_sha256'), approved_narration_sha256=sha(narration),
                evidence_note='Editorial assessment, not measured audience retention' if current else
                'Owner wording differs from the reviewed draft; prior editorial notes are historical, not revalidated')

def feedback_context():
    from .core import db
    fields = ('reel_id','publication_date','observed_at','period','source','source_definitions','runtime_seconds',
              'views','viewers','reach','average_watch_seconds','retention_observations','shares','comments','follows')
    with db() as c:rows=c.execute('SELECT payload FROM metrics ORDER BY id DESC LIMIT 10').fetchall()
    observations = [{k:v for k,v in json.loads(row['payload']).items() if k in fields} for row in rows]
    return dict(observations=observations, interpretation='Owner-recorded observational data; samples may be tiny, incomplete or biased. No causal claim or viral prediction. Views are not unique viewers. Never infer completion rate from average watch time/runtime. Consider patterns over multiple Reels, never automatically rewrite policy from one result.')

def validate_feedback(payload):
    import math
    from datetime import datetime
    for key in ('views','viewers','reach','shares','comments','follows','average_watch_seconds','runtime_seconds'):
        value=payload.get(key)
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (key=='runtime_seconds' and value==0)):
            raise ValueError('Metrics must be actual finite nonnegative numbers; runtime must be positive')
    extended=any(k in payload for k in ('reel_id','publication_date','runtime_seconds','viewers','retention_observations'))
    if extended and (not payload.get('observed_at') or not payload.get('source_definitions')):
        raise ValueError('Extended performance observations need observed_at and source_definitions')
    for key in ('observed_at','publication_date'):
        if payload.get(key):
            try:datetime.fromisoformat(str(payload[key]).replace('Z','+00:00'))
            except ValueError:raise ValueError(key+' must be an ISO date or datetime')
