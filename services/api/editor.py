"""Validated editable drafts. Deterministic media work runs only in the native worker."""
import copy
import math
import os
import subprocess
from array import array
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from .core import ROOT, STORE, episode, epdir, read_json, now, sha, update_episode
from .file_writer import EpisodeWriter, episode_lock
from .creative import approved, clean_words
from .media import timeline, mix_audio, verify_timeline, fingerprint
from .activity import emit

RUNTIME_FILES = ('src/index.tsx','src/composition.tsx','render.mjs')

def provision_runtime(directory):
    """Explicit editor-v1 artifact; never replace an episode's historical input snapshot."""
    writer=EpisodeWriter(directory)
    records={}
    for relative in RUNTIME_FILES:
        raw=(ROOT/'video/remotion'/relative).read_bytes()
        dest='06_edit/remotion/editor-v1/'+relative
        if writer.path(dest).exists():
            # An older episode keeps its own installed copy (never overwritten); the plan pins that copy's hash.
            records[relative]=sha(writer.path(dest).read_bytes())
            continue
        writer.bytes(dest,raw,replace=False)
        records[relative]=sha(raw)
    return records

def validate_runtime(directory, plan):
    writer=EpisodeWriter(directory)
    for name,digest in plan['runtime'].items():
        if name not in RUNTIME_FILES:raise ValueError('Unknown editor runtime file')
        if sha(writer.path('06_edit/remotion/editor-v1/'+name).read_bytes())!=digest:raise ValueError('Editor runtime integrity failure')

def waveform(path, duration):
    # 400 samples/s is enough for an overview. Read bounded PCM, not compressed-file guesses.
    result=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-t',str(duration),'-ac','1','-ar','400','-f','s16le','pipe:1'],capture_output=True,timeout=180)
    if result.returncode:raise ValueError('Could not decode waveform')
    samples=array('h');samples.frombytes(result.stdout)
    return [round(max((abs(x)/32768 for x in samples[i:i+4]),default=0),5) for i in range(0,len(samples),4)]

def prepare(eid, jid):
    if os.getenv('ODD_EPISODE_WORKER')!='1':raise ValueError('Draft preparation requires verified episode isolation')
    from .media import validate_assets
    ep=episode(eid);approved(ep);directory=epdir(ep);writer=EpisodeWriter(directory)
    plan=read_json(directory/'06_edit/edit_plan.json')
    validate_runtime(directory,plan)
    def event(kind,message,**details):emit(directory,'render-'+str(jid),eid,'deterministic','Auto edit',kind,message,**details)
    event('job.started','Validating uploaded assets and supplied subtitle timing')
    report=validate_assets(eid)
    if not report['valid']:raise ValueError('; '.join(report['errors']))
    event('stage.completed','Assets validated',completed=len(report['images'])+3,total=len(ep['data']['package']['scenes'])+3)
    props=timeline(eid,report,write=False)
    for c in props['captions']:
        c.update(size=1,glow_strength=1,glow=c.get('glow',True),emphasis=c.get('emphasis','none'),
                 enter_frames=c.get('enter_frames',props['style'].get('wave',{}).get('entrance_frames',5)),
                 exit_frames=c.get('exit_frames',props['style'].get('wave',{}).get('exit_frames',0)))
        c['enter_frames']=min(c['enter_frames'],c['end']-c['start']);c['exit_frames']=min(c['exit_frames'],c['end']-c['start'])
    event('ai.activity','Measuring narration and preparing the continuous two-source instrumental bed')
    mix=mix_audio(eid,report,output_directory=f'06_edit/audio/draft-{jid}')
    writer.json('06_edit/audio_mix.json',mix)
    duration=props['durationInFrames']/30
    waves={role:waveform(STORE/mix[key],duration) for role,key in [('narration','narration'),('music','instrumental')]}
    envelope=[min(1,max(waves['narration'][int(f/30*100):int((f+1)/30*100)+1],default=0)*3) for f in range(props['durationInFrames'])]
    props.update(editor_version=1,narration=mix['narration'],instrumental=mix['instrumental'],
                 audio=dict(narration_gain=1,music_gain=1,fade_in=0,fade_out=0,ducking=0,envelope=envelope))
    plan.update(created=now(),method='SRT-grounded timing; validated per-boundary transition decisions (decisions file, storyboard AI hints or deterministic fallback) within the pinned profile; emphasis and caption rules; measured FFmpeg mix',
                baseline=props,asset_fingerprints=report['fingerprints'],audio_measurements=mix,
                prepared_audio_hashes={k:fingerprint(STORE/mix[k]) for k in ('narration','instrumental')})
    writer.json('06_edit/edit_plan.json',plan)
    writer.json('06_edit/waveforms.json',dict(source_hashes={k:fingerprint(STORE/mix[k]) for k in ('narration','instrumental')},peaks=waves))
    writer.json('06_edit/timeline.json',props);writer.json('06_edit/captions.json',props['captions'])
    revdir=writer.path('06_edit/revisions');revdir.mkdir(parents=True,exist_ok=True)
    revision=max([0]+[int(p.stem) for p in revdir.glob('*.json') if p.stem.isdigit()])+1
    writer.json(f'06_edit/revisions/{revision:06d}.json',props,replace=False)
    writer.json('06_edit/editor_state.json',dict(revision=revision,updated=now(),ready=True))
    for name in ('timeline.json','captions.json','audio_mix.json','waveforms.json','editor_state.json'):
        event('file.saved','Editable draft file verified',file='06_edit/'+name)
    from . import studio
    forced=bool(read_json(writer.path(f'.production/jobs/{jid}.json')).get('replace_studio_edits'))
    def say(stage,message):emit(directory,'render-'+str(jid),eid,'deterministic',stage,'stage.completed',message)
    try:
        studio.generate(directory,props,ep['data']['package']['scenes'],ep['code'],force=forced,source_revision=revision,emit=say)
        say('Ready to edit','Remotion Studio project is ready to open')
    except ValueError as exc:
        if 'has your edits' not in str(exc):raise
        event('ai.activity','Your existing Remotion Studio edits were kept and not replaced: '+str(exc))
    update_episode(eid,'EDIT_READY',error=None,message='Automatic edit ready. Open it in Remotion Studio, make small adjustments, then render the final video.')
    event('job.completed','Draft ready for review. Open Live Editor; no MP4 render was launched.',status='COMPLETE')

class CaptionEdit(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    text:str=Field(min_length=1,max_length=160)
    start:StrictInt=Field(ge=0)
    end:StrictInt=Field(ge=1)
    y:float=Field(ge=.17,le=.73)
    preset:str
    emphasis:str='none'
    enter_frames:StrictInt=Field(default=5,ge=0,le=30)
    exit_frames:StrictInt=Field(default=2,ge=0,le=30)
    glow:bool=True
    size:float=Field(default=1,ge=.8,le=1)
    glow_strength:float=Field(default=1,ge=0,le=2)

class SceneEdit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str
    transition:str
    transition_frames:StrictInt=Field(ge=0,le=30)

class AudioEdit(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    # Full range: silence up to +6 dB (gain 2) for both sources; fades up to 10 s; ducking up to full.
    narration_gain:float=Field(ge=0,le=2)
    music_gain:float=Field(ge=0,le=2)
    fade_in:StrictInt=Field(ge=0,le=300)
    fade_out:StrictInt=Field(ge=0,le=300)
    ducking:float=Field(ge=0,le=1)

class Edit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:StrictInt=Field(ge=1)
    captions:list[CaptionEdit]=Field(min_length=1,max_length=3000)
    scenes:list[SceneEdit]=Field(min_length=1,max_length=1000)
    audio:AudioEdit

def validate_edit(ep,plan,payload):
    patch=Edit.model_validate(payload)
    base=plan['baseline'];props=copy.deepcopy(base)
    if [x.id for x in patch.scenes]!=[x['id'] for x in base['scenes']]:raise ValueError('Scene identity and order are locked to the storyboard')
    if clean_words(' '.join(x.text for x in patch.captions))!=clean_words(ep['data']['script']['narration']):
        raise ValueError('Caption words must preserve the approved narration, in order')
    allowed={'quick_pop','immediate_reveal','gentle_emphasis'} if props['style']['renderer']=='classic' else {'quick_pop','wave_reveal','glow_pop','smooth_replace','immediate_impact','soft_fade'}
    if len(patch.captions)!=len(base['captions']):raise ValueError('Keep the narration-grounded phrase grouping')
    previous=0
    for i,c in enumerate(patch.captions):
        # A minor correction is bounded to two frames from the trusted cue, never fabricated alignment.
        original=base['captions'][i]
        if abs(c.start-original['start'])>2 or abs(c.end-original['end'])>2:raise ValueError('Timing corrections are limited to two frames from the supplied cue')
        if c.start<previous or c.end>props['durationInFrames'] or c.preset not in allowed or c.emphasis not in ('none','gold'):
            raise ValueError('Invalid caption timing, preset or emphasis')
        if len(clean_words(c.text))>4:raise ValueError('Captions require one to four words')
        shot=next(s for s in props['scenes'] if s['start']<=c.start<s['end'])
        if c.end>shot['end']:raise ValueError('Captions cannot cross scene boundaries')
        scene=next(s for s in ep['data']['package']['scenes'] if s['scene_id']==shot['id'])
        for r in scene['protected_regions']:
            if .09<r['x']+r['width'] and .91>r['x'] and c.y-.065<r['y']+r['height'] and c.y+.065>r['y']:
                raise ValueError('Caption overlaps an authored protected region')
        previous=c.end
    props['captions']=[c.model_dump() for c in patch.captions]
    for shot,change in zip(props['scenes'],patch.scenes):shot.update(change.model_dump())
    props['audio'].update(patch.audio.model_dump())
    verify_timeline(props)
    return props

def load(eid):
    ep=episode(eid);directory=epdir(ep);writer=EpisodeWriter(directory)
    if not writer.path('06_edit/editor_state.json').exists():raise ValueError('Auto Edit has not prepared this episode. Validate the assets first.')
    plan=read_json(writer.path('06_edit/edit_plan.json'));validate_runtime(directory,plan)
    # Browser and export must use the same version. Do not silently preview with a newer engine.
    for name,digest in plan['runtime'].items():
        if sha((ROOT/'video/remotion'/name).read_bytes())!=digest:raise ValueError('This draft requires its matching editor version; its saved runtime and historical exports are preserved')
    state=read_json(writer.path('06_edit/editor_state.json'))
    if not state.get('ready'):raise ValueError('An explicit draft rebuild is in progress. Follow AI Activity; prior revisions are preserved.')
    return dict(timeline=read_json(writer.path(f'06_edit/revisions/{state["revision"]:06d}.json')),baseline=plan['baseline'],state=state,
                waveforms=read_json(writer.path('06_edit/waveforms.json'))['peaks'],title=ep['title'],
                revisions=sorted(int(p.stem) for p in writer.path('06_edit/revisions').glob('*.json') if p.stem.isdigit()))

def save(eid,payload):
    ep=episode(eid);approved(ep);directory=epdir(ep);writer=EpisodeWriter(directory)
    with episode_lock(directory,'media',blocking=False),episode_lock(directory,'editor'):
        ep=episode(eid)
        if ep['status'] in ('QUEUED','RENDERING'):raise ValueError('Wait for the active job before saving edits')
        state=read_json(writer.path('06_edit/editor_state.json'))
        if not state.get('ready'):raise ValueError('The draft rebuild has not completed. Retry Rebuild Draft before saving edits.')
        if payload.get('revision')!=state['revision']:raise ValueError('Revision conflict. Reload this draft before saving; another tab changed it.')
        plan=read_json(writer.path('06_edit/edit_plan.json'));validate_runtime(directory,plan)
        props=validate_edit(ep,plan,payload)
        for relative,digest in plan['asset_fingerprints'].items():
            if fingerprint(writer.path(relative))!=digest:raise ValueError('An asset changed. Prepare a new draft explicitly before editing.')
        revision=max([state['revision']]+[int(p.stem) for p in writer.path('06_edit/revisions').glob('*.json') if p.stem.isdigit()])+1
        writer.json(f'06_edit/revisions/{revision:06d}.json',props,replace=False)
        writer.json('06_edit/timeline.json',props);writer.json('06_edit/captions.json',props['captions'])
        writer.json('06_edit/editor_state.json',dict(revision=revision,updated=now(),ready=True))
        update_episode(eid,'EDIT_READY',message=f'Editable revision {revision} saved; no video render requested')
        return dict(revision=revision)

def needs_rebuild(eid,report):
    ep=episode(eid);directory=epdir(ep)
    if not (directory/'06_edit/editor_state.json').exists():return False
    if not read_json(directory/'06_edit/editor_state.json').get('ready'):return True
    plan=read_json(directory/'06_edit/edit_plan.json')
    from .styles import effective_style
    return (plan.get('asset_fingerprints')!=report.get('fingerprints') or
            plan['baseline']['style']['profile_id']!=effective_style(ep)['profile_id'])
