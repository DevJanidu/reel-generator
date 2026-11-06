import json
import math
import re
import subprocess
from pathlib import Path
from PIL import Image
from .core import ROOT, STORE, now, sha, read_json, write_json, episode, epdir
from .creative import approved, clean_words
from . import styles

IMAGE_EXT={'.png','.jpg','.jpeg','.webp'}
AUDIO_EXT={'.wav','.mp3','.m4a','.aac','.flac','.ogg'}

def command(args, timeout=180, progress=None):
    result=subprocess.run([str(a) for a in args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    if result.returncode:
        raise ValueError(f'{Path(str(args[0])).name} failed: {result.stderr[-2500:]}')
    return result.stdout+result.stderr

def probe(path):
    return json.loads(command(['ffprobe','-v','error','-show_format','-show_streams','-of','json',path]))

def decoded(path):
    command(['ffmpeg','-v','error','-i',path,'-f','null','-'],timeout=300)

def fingerprint(path):
    # Content hashing deliberately detects same-size/same-mtime replacement too.
    return sha(path.read_bytes())

def parse_srt(path):
    text=path.read_text(encoding='utf-8-sig').replace('\r\n','\n').strip()
    cues=[]
    def seconds(value):
        h,m,s,ms=map(int,re.split(r'[:,.]',value))
        if m>59 or s>59:
            raise ValueError('Invalid SRT time component')
        return h*3600+m*60+s+ms/1000
    for block in re.split(r'\n\s*\n',text):
        lines=block.splitlines()
        if len(lines)<3 or not lines[0].strip().isdigit():
            raise ValueError('SRT requires numbered cues and timestamp lines')
        match=re.fullmatch(r'(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})',lines[1].strip())
        if not match:
            raise ValueError('Invalid SRT timestamp: '+lines[1])
        start,end=map(seconds,match.groups()); content=' '.join(lines[2:]).strip()
        if '<' in content or '{' in content:
            raise ValueError('Supply clean caption text without styling markup')
        if end<=start or (cues and start<cues[-1]['end']):
            raise ValueError('SRT cues overlap or have nonpositive duration')
        if not clean_words(content):
            raise ValueError('Empty subtitle cue')
        cues.append(dict(start=start,end=end,text=content,index=int(lines[0])))
    if not cues:
        raise ValueError('No subtitle cues found')
    return cues

_FUNCTION_WORDS={'the','a','an','of','to','and','in','on','at','by','for','with','his','her','their','its','our','my','your','but','or','that','as','from','into','than','then','was','were'}

def _partition_phrases(units):
    """Split [(text,clean_word_count),...] into chunks of 2-4 words (1 only if unavoidable).
    Prefers breaks after punctuation and avoids ending on a function word."""
    n=len(units)
    INF=float('inf'); best=[INF]*(n+1); prev=[0]*(n+1); best[0]=0
    only_one=sum(u[1] for u in units)<=1
    for i in range(1,n+1):
        size=0
        for j in range(i-1,-1,-1):
            size+=units[j][1]
            if size>4 and j<i-1:break
            last=units[i-1][0]
            cost={1:0 if only_one else 6,2:1,3:0,4:.3}.get(size,10)
            if re.search(r'[.,;:!?…—–"”)\]]$',last):cost-=3
            else:
                cost+=.5
                words=clean_words(last)
                if words and words[-1] in _FUNCTION_WORDS:cost+=2
            if best[j]+cost<best[i]:best[i]=best[j]+cost;prev[i]=j
    chunks=[];i=n
    while i>0:
        chunks.append(units[prev[i]:i]);i=prev[i]
    return chunks[::-1]

def phrase_cues(cues,scenes):
    """Auto-split long SRT cues into 2-4 word phrases and cut at scene boundaries.
    Text is preserved exactly. Timing inside a split cue is ESTIMATED proportionally to
    character length between the real cue start/end; cues that are already 1-4 words and do not
    cross a scene boundary keep their original timing untouched."""
    bounds=set();off=0
    for scene in scenes:
        bounds.add(off);off+=len(clean_words(scene['narration_text']))
    out=[];offset=0;split=0
    for c in cues:
        units=[]
        for tok in c['text'].split():
            n=len(clean_words(tok))
            if n==0 and units:units[-1][0]+=' '+tok
            else:units.append([tok,n])
        if len(units)>1 and units[0][1]==0:
            units[1][0]=units[0][0]+' '+units[1][0];units=units[1:]
        forced=set();cum=0
        for i,u in enumerate(units):
            if i>0 and (offset+cum) in bounds:forced.add(i)
            cum+=u[1]
        total=cum;offset+=total
        if total<=4 and not forced:
            out.append(dict(c));continue
        split+=1
        cut=[0]+sorted(forced)+[len(units)];pieces=[]
        for a,b in zip(cut,cut[1:]):
            if b>a:pieces+=_partition_phrases(units[a:b])
        texts=[' '.join(u[0] for u in p) for p in pieces]
        weights=[max(1,len(re.sub(r'\W','',t))) for t in texts]
        span=c['end']-c['start'];wsum=sum(weights);t0=c['start'];acc=0
        for k,text in enumerate(texts):
            acc+=weights[k]
            t1=c['end'] if k==len(texts)-1 else round(c['start']+span*acc/wsum,3)
            if t1<=t0:t1=round(t0+.001,3)
            out.append(dict(start=t0,end=t1,text=text,index=0));t0=t1
    for i,c in enumerate(out,1):c['index']=i
    return out,split

def validate_assets(eid):
    ep=episode(eid); approved(ep); directory=epdir(ep)
    if not ep['data'].get('package'):
        raise ValueError('Preproduction is not complete')
    report=dict(episode_id=ep['code'],checked_at=now(),valid=False,errors=[],warnings=[],images={},sources={},fingerprints={},timing_evidence='Supplied SRT cue boundaries; not independently forced-aligned to audio')
    from .file_writer import no_links
    from .snapshots import validate
    pin=validate(directory)
    errors=report['errors']; warnings=report['warnings']
    cachefile=directory/'reports/ASSET_DECODE_CACHE.json'
    cache=read_json(cachefile) if cachefile.exists() else {}
    newcache={}
    def inspect(path,kind):
        no_links(path)
        key=str(path.relative_to(directory)); digest=fingerprint(path)
        report['fingerprints'][key]=digest
        if cache.get(key,{}).get('sha256')==digest:
            info=cache[key]['info']
        elif kind=='image':
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                info=dict(width=img.width,height=img.height,animated=bool(getattr(img,'is_animated',False)))
            if info['animated']:
                raise ValueError('Animated image inputs are prohibited')
        else:
            info=probe(path); decoded(path)
        newcache[key]=dict(sha256=digest,info=info)
        return info
    required=[s['scene_id'] for s in ep['data']['package']['scenes']]
    imagefiles=list((directory/'05_assets/images').iterdir())
    for sid in required:
        found=[p for p in imagefiles if p.stem.upper()==sid and p.suffix.lower() in IMAGE_EXT]
        if len(found)!=1:
            errors.append(f'{sid}: need exactly one decodable {sid}.png/.jpg/.webp; found {len(found)}')
            continue
        try:
            info=inspect(found[0],'image')
            # Owner-supplied stills: aspect ratio/resolution are not policed here.
            # The renderer uses objectFit:contain, so artwork is never stretched.
            # The file must still decode (checked by inspect above).
            report['images'][sid]=dict(path=str(found[0].relative_to(STORE)).replace('\\','/'),**info)
        except Exception as exc:
            errors.append(sid+': '+str(exc))
    for kind in ['narration','music','subtitles']:
        files=[p for p in (directory/f'05_assets/{kind}').iterdir() if p.is_file() and p.suffix.lower() in ({'.srt'} if kind=='subtitles' else AUDIO_EXT)]
        if len(files)!=1:
            errors.append(f'{kind}: need exactly one usable file; found {len(files)}. Remove obsolete alternatives.')
            continue
        try:
            if kind=='subtitles':
                report['fingerprints'][str(files[0].relative_to(directory))]=fingerprint(files[0])
                source_cues=parse_srt(files[0])
                report['cues'],split=phrase_cues(source_cues,(ep['data'].get('package') or {}).get('scenes',[]))
                if split:
                    warnings.append(f'{split} long SRT cue(s) were automatically re-phrased into 2-4 word captions at scene boundaries. Text is unchanged; timing inside those cues is estimated from character length, so check caption sync by ear. Your SRT file was not modified.')
                info={}
            else:
                info=inspect(files[0],'audio')
                audios=[s for s in info['streams'] if s['codec_type']=='audio']
                if len(audios)!=1 or any(s['codec_type']=='video' and not s.get('disposition',{}).get('attached_pic') for s in info['streams']):
                    raise ValueError('must contain one audio stream and no video')
                duration=float(info['format']['duration'])
                if duration<=0:
                    raise ValueError('zero duration audio')
                info=dict(duration=duration,sample_rate=audios[0]['sample_rate'])
            report['sources'][kind]=dict(path=str(files[0].relative_to(STORE)).replace('\\','/'),**info)
        except Exception as exc:
            errors.append(kind+': '+str(exc))
    rights=ep['data'].get('music_rights',{})
    if pin['signature_music']['status']=='PINNED' and 'music' in report['sources']:
        actual=STORE/report['sources']['music']['path']
        if fingerprint(actual)!=pin['signature_music']['sha256']:errors.append('Instrumental differs from this episode\'s immutable pinned signature music')
    if not rights.get('instrumental_confirmed'):
        errors.append('Music: confirm the uploaded track is instrumental (automated vocal detection is not claimed)')
    if not rights.get('evidence'):
        warnings.append('Music rights evidence is missing; no license has been verified or inferred')
    cues=report.get('cues',[])
    if cues:
        if clean_words(' '.join(c['text'] for c in cues))!=clean_words(ep['data']['script']['narration']):
            errors.append('Subtitle text does not cover the exact approved narration in order')
        if any(len(clean_words(c['text']))>4 for c in cues):
            errors.append('SRT has cues over four words. Supply phrase-level 1–4-word cues or genuine alignment; word timing will not be invented.')
        duration=report['sources'].get('narration',{}).get('duration')
        if duration and cues[-1]['end']>duration+.05:
            errors.append('Subtitle end extends beyond actual narration duration')
        if duration and duration-cues[-1]['end']>1.5:
            warnings.append('Narration has more than 1.5s after the last cue; verify trailing silence and timing')
        # Each scene starts at an observed cue boundary, never an invented intra-cue word time.
        boundaries={0:0.0}; offset=0
        for c in cues:
            boundaries[offset]=c['start']; offset+=len(clean_words(c['text']))
        offset=0
        for scene in ep['data']['package']['scenes']:
            if offset not in boundaries:
                errors.append(scene['scene_id']+': narration starts inside an SRT cue. Split/correct the SRT at this scene boundary.')
            offset+=len(clean_words(scene['narration_text']))
    warnings.append('SRT syntax, text coverage and bounds are verified; acoustic alignment and vocal/instrumental identity require supplied evidence or human listening.')
    report['valid']=not errors
    write_json(cachefile,newcache)
    write_json(directory/'reports/ASSET_VALIDATION.json',report)
    return report

def caption_position(scene):
    # Conservative two-line text box; x bounds mirror composition geometry.
    def free(y):
        box=(.09,y-.065,.82,.13)
        for r in scene['protected_regions']:
            if box[0]<r['x']+r['width'] and box[0]+box[2]>r['x'] and box[1]<r['y']+r['height'] and box[1]+box[3]>r['y']:
                return False
        return True
    # Candidates stay within the guide's safe band (about y .105-.775 of frame height).
    for y in [scene['caption_y'],.46,.35,.58,.24,.68,.21,.17,.73]:
        if free(y):
            return y
    raise ValueError(scene['scene_id']+': no safe caption zone. Adjust authored protected regions/composition.')

def verify_timeline(props):
    """Machine check of the edit plan: contiguous scenes, static stills, only allowed transitions, overlap accounting.
    Transitions are layered over scene boundaries and never move a boundary, so total duration cannot change."""
    scenes=props['scenes']; style=props.get('style') or {}
    allowed=style.get('allowed_transitions',['cut']); cursor=0
    for i,shot in enumerate(scenes):
        if shot['start']!=cursor or shot['end']<=shot['start']:
            raise ValueError(shot['id']+': scene boundaries must be contiguous and positive')
        cursor=shot['end']
        if shot.get('motion')!='static':
            raise ValueError(shot['id']+': stills must stay static')
        t=shot.get('transition','cut'); f=shot.get('transition_frames',0)
        if t not in allowed or t not in ('cut','crossfade','dip_to_dark'):
            raise ValueError(shot['id']+': transition '+str(t)+' is not allowed by the pinned style')
        if i==0 and t!='cut':
            raise ValueError('The first scene cannot have a transition')
        if t!='cut':
            shorter=min(scenes[i-1]['end']-scenes[i-1]['start'],shot['end']-shot['start'])
            limit=shorter//2*(1 if t=='crossfade' else 2)
            if f<1 or f>limit:
                raise ValueError(f"{shot['id']}: {t} needs {f} frames but only {limit} fit inside the neighbouring scenes")
    if cursor!=props['durationInFrames']:
        raise ValueError('Scenes must cover exactly the narration duration')
    for c in props['captions']:
        if c['end']<=c['start'] or c.get('enter_frames',0)>(c['end']-c['start']) or c.get('exit_frames',0)>(c['end']-c['start']):
            raise ValueError('Caption animation does not fit inside its phrase window')
    return True

def timeline(eid,report,style=None,extra_overrides=None,write=True):
    ep=episode(eid); approved(ep)
    if not report['valid']:
        raise ValueError('Asset validation failed: '+'; '.join(report['errors']))
    cues=report['cues']; duration=report['sources']['narration']['duration']; fps=30
    frames=math.ceil(duration*fps)
    starts={}; count=0
    for cue in cues:
        starts[count]=cue['start']; count+=len(clean_words(cue['text']))
    result=[]; offset=0
    for i,scene in enumerate(ep['data']['package']['scenes']):
        start=0 if i==0 else math.ceil(starts[offset]*fps)
        end_offset=offset+len(clean_words(scene['narration_text']))
        end=frames if i==len(ep['data']['package']['scenes'])-1 else math.ceil(starts[end_offset]*fps)
        if end<=start:
            raise ValueError('Scene duration is not positive at observed cue boundaries')
        result.append(dict(id=scene['scene_id'],start=start,end=end,image=report['images'][scene['scene_id']]['path'],caption_y=caption_position(scene),motion='static',transition='cut'))
        offset=end_offset
    # Editing profile pinned by this episode (never the global default): validated transitions + caption presets.
    style=style or styles.effective_style(ep); profile=style['profile']
    package_scenes=ep['data']['package']['scenes']
    overrides={**(ep['data'].get('style_overrides') or {}).get('transitions',{}),**(extra_overrides or {})}
    decisions=styles.load_decisions(epdir(ep),package_scenes)
    plan,transition_notes=styles.resolve_transitions(package_scenes,[r['end']-r['start'] for r in result],profile,overrides,decisions)
    for shot,item in zip(result,plan):
        shot.update(transition=item['transition'],transition_frames=item['frames'],transition_reason=item['reason'],
                    transition_editorial=item['editorial'],transition_purpose=item['purpose'],transition_source=item['source'])
    captions=[]; offsets=[]; word_offset=0
    for cue in cues:
        start=math.ceil(cue['start']*fps); end=min(frames,math.ceil(cue['end']*fps))
        if end<=start:
            raise ValueError('Subtitle cue is too short for 30 FPS')
        scene=next((s for s in result if s['start']<=start<s['end']),None)
        if not scene:
            raise ValueError('Caption outside scene coverage')
        captions.append(dict(start=start,end=end,text=cue['text'],y=scene['caption_y'],preset='quick_pop',timing='supplied SRT cue'))
        offsets.append(word_offset); word_offset+=len(clean_words(cue['text']))
    styles.assign_caption_presets(captions,result,package_scenes,offsets,profile)
    props=dict(episode_id=ep['code'],width=1080,height=1920,fps=30,durationInFrames=frames,scenes=result,captions=captions,audioSources=['narration','instrumental'],approved_script_sha256=ep['data']['approval']['sha256'],asset_fingerprints=report['fingerprints'],
               style=styles.renderer_style(style,transition_notes))
    verify_timeline(props)
    if write:
        write_json(epdir(ep)/'06_edit/timeline.json',props)
        write_json(epdir(ep)/'06_edit/captions.json',captions)
    return props

def loudness(path):
    result=command(['ffmpeg','-hide_banner','-i',path,'-af','loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json','-f','null','-'],timeout=300)
    matches=re.findall(r'\{\s*"input_i".*?\}',result,re.S)
    if not matches:
        raise ValueError('FFmpeg did not return measured loudness')
    info=json.loads(matches[-1])
    if not math.isfinite(float(info['input_i'])):
        raise ValueError('Audio is silent or unmeasurable')
    return info

def mix_audio(eid,report,offset_override=None,preview=False,output_directory=None):
    ep=episode(eid); directory=epdir(ep); output=directory/('06_edit/audio_preview' if preview else '06_edit')
    if preview:output.mkdir(parents=True,exist_ok=True)
    if output_directory is not None:
        from .file_writer import EpisodeWriter
        output=EpisodeWriter(directory).path(output_directory);output.mkdir(parents=True,exist_ok=True)
    narration=STORE/report['sources']['narration']['path']; music=STORE/report['sources']['music']['path']
    speech_info=loudness(narration); music_info=loudness(music)
    speech=output/'narration_normalized.wav'; bed=output/'instrumental_ducked.wav'
    duration=report['sources']['narration']['duration']
    # Two-pass measured normalization for speech; headroom accommodates the music layer.
    filt=f"loudnorm=I=-18:TP=-3:LRA=9:measured_I={speech_info['input_i']}:measured_TP={speech_info['input_tp']}:measured_LRA={speech_info['input_lra']}:measured_thresh={speech_info['input_thresh']}:offset={speech_info['target_offset']}:linear=true"
    # Re-measure for the actual -18 target so the two-pass offset matches its target.
    raw=command(['ffmpeg','-hide_banner','-i',narration,'-af','loudnorm=I=-18:TP=-3:LRA=9:print_format=json','-f','null','-'])
    m=json.loads(re.findall(r'\{\s*"input_i".*?\}',raw,re.S)[-1])
    filt=f"loudnorm=I=-18:TP=-3:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    command(['ffmpeg','-y','-v','error','-i',narration,'-af',filt,'-ar','48000','-ac','2',speech])
    normalized=loudness(speech)
    # Owner music-level offset (dB, + louder / - quieter) relative to the automatic 21 dB narration-over-music gap.
    offset_db=max(-12.0,min(6.0,float(offset_override if offset_override is not None else (ep['data'].get('music_mix') or {}).get('offset_db',0))))
    target=float(normalized['input_i'])-21+offset_db
    gain=target-float(music_info['input_i'])
    fade=min(.6,duration/5)
    graph=f"[0:a]volume={gain}dB,afade=t=in:d={fade},afade=t=out:st={max(0,duration-fade)}:d={fade}[bed];[bed][1:a]sidechaincompress=threshold=0.035:ratio=3:attack=100:release=600:makeup=1[out]"
    command(['ffmpeg','-y','-v','error','-stream_loop','-1','-i',music,'-i',speech,'-filter_complex',graph,'-map','[out]','-t',str(duration),'-ar','48000','-ac','2',bed],timeout=300)
    bed_info=loudness(bed)
    # Re-measure the ducked bed, then correct its integrated level while preserving its envelope.
    # This prevents a louder narrator from unintentionally pushing the entire music bed far below target.
    correction=max(-6,min(6,target-float(bed_info['input_i'])))
    balanced=output/'instrumental_balanced.wav'
    command(['ffmpeg','-y','-v','error','-i',bed,'-af',f'volume={correction}dB',balanced])
    from .file_writer import EpisodeWriter
    EpisodeWriter(directory).rename(balanced.relative_to(directory).as_posix(),bed.relative_to(directory).as_posix())
    bed_info=loudness(bed)
    mix=dict(sources=['narration','instrumental'],sfx=False,narration=str(speech.relative_to(STORE)).replace('\\','/'),instrumental=str(bed.relative_to(STORE)).replace('\\','/'),
             input_speech=speech_info,input_music=music_info,normalized_speech=normalized,ducked_music=bed_info,
             initial_gap_db=21,owner_music_offset_db=offset_db,measured_integrated_gap_db=float(normalized['input_i'])-float(bed_info['input_i']),music_gain_db=gain,post_duck_balance_correction_db=correction,
             ducking=dict(threshold=.035,ratio=3,attack_ms=100,release_ms=600),rights=ep['data'].get('music_rights'),
             warnings=['Integrated level separation is measured; moment-to-moment intelligibility and pumping still benefit from listening.'])
    if preview:
        # Listening copy only: narration + ducked instrumental in one file. Never used by the final render.
        command(['ffmpeg','-y','-v','error','-i',speech,'-i',bed,'-filter_complex','amix=inputs=2:duration=longest:normalize=0','-c:a','aac','-b:a','160k',output/'preview_mix.m4a'],timeout=180)
        write_json(output/'preview_mix.json',mix)
        return mix
    write_json(output/'audio_mix.json',mix)
    return mix

def technical_qc(path,props,preview=False):
    info=probe(path); decoded(path)
    videos=[s for s in info['streams'] if s['codec_type']=='video']; audios=[s for s in info['streams'] if s['codec_type']=='audio']
    if len(videos)!=1 or len(audios)!=1:
        raise ValueError('Encoded media requires one video and one mixed audio stream')
    video=videos[0]; expected=(540,960) if preview else (1080,1920)
    if (video['width'],video['height'])!=expected or video['codec_name']!='h264' or video['r_frame_rate']!='30/1' or audios[0]['codec_name']!='aac':
        raise ValueError('Encoded codec/dimensions/FPS mismatch')
    if abs(float(info['format']['duration'])-props['durationInFrames']/30)>.2:
        raise ValueError('Encoded duration mismatch')
    black=command(['ffmpeg','-hide_banner','-i',path,'-vf','blackdetect=d=0.04:pix_th=0.01:pic_th=0.995','-an','-f','null','-'])
    if 'black_start:' in black:
        raise ValueError('Black frame interval detected; inspect illustration coverage')
    levels=loudness(path)
    if float(levels['input_tp'])>-.5:
        raise ValueError('True peak exceeds export headroom')
    if not preview and abs(float(levels['input_i'])+16)>1.5:
        raise ValueError('Final integrated loudness is outside the -16 LUFS ±1.5 target')
    return dict(valid=True,path=str(path.relative_to(STORE)),video=video,audio=audios[0],loudness=levels,decoded=True,no_black_intervals=True,
                machine_verified=['codec/dimensions/fps','full decode','duration','no black intervals','true peak','timeline/asset coverage','static image composition policy','scene-transition overlap accounting (duration unchanged)','two intended audio sources'],
                human_review_benefits=['Illustration identity and emotional payoff','SRT acoustic accuracy','Instrumental vocal absence and rights','Phone/headphone intelligibility and pumping','Faces/clues versus authored safe regions'])
