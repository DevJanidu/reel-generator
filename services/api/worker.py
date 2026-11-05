import json
import os
import subprocess
import threading
import time
import sys
from pathlib import Path
from .core import ROOT, STORE, now, db, episode, epdir, update_episode, read_json, write_json, textfile
from .creative import approved
from .media import validate_assets, timeline, mix_audio, technical_qc, fingerprint, command, loudness, probe, decoded
from .file_writer import EpisodeWriter,episode_lock
from . import isolation
from .activity import emit

stop=threading.Event()

def enqueue(eid,kind='draft'):
    with episode_lock(epdir(episode(eid)),'editor'):
        return _enqueue(eid,kind)

def _enqueue(eid,kind='draft',rebuild=False):
    ep=episode(eid); approved(ep)
    if not ep['data'].get('package'):
        raise ValueError('Preproduction is incomplete')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        found=c.execute("SELECT id FROM jobs WHERE episode_id=? AND status IN ('QUEUED','RUNNING')",(eid,)).fetchone()
        if found:
            return found['id']
        if kind=='draft':
            from .editor import provision_runtime
            writer=EpisodeWriter(epdir(ep))
            if writer.path('06_edit/editor_state.json').exists() and not rebuild:raise ValueError('A saved draft already exists. Open Live Editor; saved edits will not be replaced.')
            runtime=provision_runtime(epdir(ep))
            writer.json('06_edit/edit_plan.json',dict(version=1,runtime=runtime))
        elif kind!='render':raise ValueError('Unknown production job kind')
        row=c.execute('INSERT INTO jobs(episode_id,kind,status,stage,created,updated) VALUES (?,?,?,?,?,?)',(eid,kind,'QUEUED','Prepare editable draft' if kind=='draft' else 'Render saved edit',now(),now()))
    update_episode(eid,'QUEUED',error=None)
    with db() as c:job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(row.lastrowid,)).fetchone())
    if kind=='render':job['editor_revision']=read_json(epdir(ep)/'06_edit/editor_state.json')['revision']
    EpisodeWriter(epdir(ep)).json(f'.production/jobs/{row.lastrowid}.json',job)
    emit(epdir(ep),'render-'+str(row.lastrowid),eid,'deterministic' if kind=='draft' else 'remotion',kind,'job.queued','Automatic draft preparation queued' if kind=='draft' else 'Saved revision queued for final rendering')
    return row.lastrowid

def job_progress(jid,stage,value):
    if os.getenv('ODD_EPISODE_WORKER')=='1':
        root=Path(os.environ['EPISODE_WRITE_ROOT']);path=root/f'.production/jobs/{jid}.json'
        job=read_json(path)
        if job.get('stage')!=stage:emit(root,'render-'+str(jid),job['episode_id'],'remotion',stage,'ai.activity',stage)
        job.update(stage=stage,progress=value,updated=now());write_json(path,job)
        return
    with db() as c:
        c.execute('UPDATE jobs SET stage=?,progress=?,updated=? WHERE id=?',(stage,value,now(),jid))

def renderer_script(root,props):
    if props.get('editor_version')==1:
        from .editor import validate_runtime
        validate_runtime(root,read_json(root/'06_edit/edit_plan.json'))
        return root/'06_edit/remotion/editor-v1/render.mjs'
    # The renderer is the one pinned by this episode's style ('@app' only for Preview Style of an unpinned profile).
    pinned=(props.get('style') or {}).get('renderer_dir','remotion')
    if pinned=='@app':return Path(os.environ['ODD_APP_ROOT'])/'video/remotion/render.mjs'
    return root/'.production/input_snapshot'/pinned/'render.mjs'

def render(props,path,preview,jid,base,name=None,progress=True):
    propsfile=path.parent/(f'{name}_props.json' if name else ('preview_props.json' if preview else 'render_props.json'))
    write_json(propsfile,props)
    root=Path(os.environ['EPISODE_WRITE_ROOT'])
    process=subprocess.Popen(['node',str(renderer_script(root,props)),str(propsfile),str(path),'preview' if preview else 'final'],
                             cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=os.environ.copy())
    lines=[]
    for line in process.stdout:
        lines.append(line)
        if progress and line.startswith('RENDER_EVENT '):
            counts=json.loads(line[len('RENDER_EVENT '):])
            emit(root,'render-'+str(jid),episode(job_eid(root))['id'],'remotion','Rendering preview' if preview else 'Rendering final','render.progress','Frames rendered',completed=counts['renderedFrames'],total=props['durationInFrames'])
        if progress and line.startswith('PROGRESS '):
            job_progress(jid,'Rendering preview' if preview else 'Rendering final',base+float(line.split()[1])*(.18 if preview else .4))
    process.wait()
    textfile(path.parent/(f'{name}_render.log' if name else ('preview_render.log' if preview else 'final_render.log')),''.join(lines))
    if process.returncode:
        raise ValueError('Remotion failed: '+''.join(lines)[-1800:])

def process_job(job):
    if os.getenv('ODD_EPISODE_WORKER')!='1':raise ValueError('Rendering must execute inside the verified episode worker, never in the controller process')
    jid=job['id']; eid=job['episode_id']; ep=episode(eid); directory=epdir(ep)
    approval=approved(ep)
    emit(directory,'render-'+str(jid),eid,'remotion','Render saved edit','job.started','Starting saved-timeline export')
    job_progress(jid,'Validate assets',.02)
    report=validate_assets(eid)
    if not report['valid']:raise ValueError('; '.join(report['errors']))
    from .editor import validate_runtime,validate_edit,CaptionEdit
    plan=read_json(directory/'06_edit/edit_plan.json');validate_runtime(directory,plan)
    state=read_json(directory/'06_edit/editor_state.json')
    if job.get('editor_revision',state['revision'])!=state['revision']:raise ValueError('Saved revision changed after render was queued')
    props=read_json(directory/f'06_edit/revisions/{state["revision"]:06d}.json')
    if props.get('editor_version')!=1:raise ValueError('Prepare and save a Live Editor draft before final rendering')
    for relative,digest in props['asset_fingerprints'].items():
        if fingerprint(directory/relative)!=digest:raise ValueError('Asset changed after draft preparation')
    # Revalidate every saved control; never regenerate a different edit at export time.
    validated=validate_edit(ep,plan,dict(revision=state['revision'],captions=[{k:v for k,v in c.items() if k in CaptionEdit.model_fields} for c in props['captions']],
        scenes=[{k:s[k] for k in ('id','transition','transition_frames')} for s in props['scenes']],audio={k:v for k,v in props['audio'].items() if k!='envelope'}))
    props=validated
    for key,digest in plan['prepared_audio_hashes'].items():
        if fingerprint(STORE/mix_path(plan,key))!=digest:raise ValueError('Prepared audio changed after the draft was saved')
    update_episode(eid,'RENDERING',message='Assets validated; measuring and preparing two-source audio mix')
    job_progress(jid,'Measured audio normalization and ducking',.08)
    mix=plan['audio_measurements']
    from functools import partial
    from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(directory)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/'
    def url(relative):
        # Paths are stored below episodes and URL encoded independently of Windows separators.
        from urllib.parse import quote
        return base+quote((STORE/relative).relative_to(directory).as_posix(),safe='/')
    rendered={**props,'scenes':[{**s,'image':url(s['image'])} for s in props['scenes']],
              'narration':url(mix['narration']),'instrumental':url(mix['instrumental'])}
    write_json(directory/'06_edit/remotion/props.json',rendered)
    preview=directory/'06_edit/previews'/f'preview_{jid}.mp4'
    render(rendered,preview,True,jid,.15)
    job_progress(jid,'Preview technical QC',.35)
    preview_qc=technical_qc(preview,props,True)
    approved(episode(eid))
    raw=directory/'06_edit'/f'final_work_{jid}.mp4'
    render(rendered,raw,False,jid,.4)
    job_progress(jid,'Final loudness/peak normalization',.82)
    measurement=loudness(raw)
    candidate=directory/'06_edit'/f'final_qc_{jid}.mp4'
    filter_=f"loudnorm=I=-16:TP=-1.5:LRA=9:measured_I={measurement['input_i']}:measured_TP={measurement['input_tp']}:measured_LRA={measurement['input_lra']}:measured_thresh={measurement['input_thresh']}:offset={measurement['target_offset']}:linear=true"
    command(['ffmpeg','-y','-v','error','-i',raw,'-c:v','copy','-af',filter_,'-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',candidate],timeout=300)
    job_progress(jid,'Final decode, codec, coverage and audio QC',.93)
    qc=technical_qc(candidate,props)
    current=episode(eid)
    if approved(current)['sha256']!=approval['sha256']:
        raise ValueError('Approval changed during render; final export blocked')
    for relative,digest in report['fingerprints'].items():
        if fingerprint(directory/relative)!=digest:
            raise ValueError('Asset changed during rendering; retry with current assets')
    final=directory/'07_export/final'/f'{ep["code"]}_v{jid:03d}.mp4'
    EpisodeWriter(directory).path('07_export/final').mkdir(parents=True,exist_ok=True)
    EpisodeWriter(directory).rename(candidate.relative_to(directory).as_posix(),final.relative_to(directory).as_posix())
    qc['path']=str(final.relative_to(STORE)).replace('\\','/')
    qc['preview']=preview_qc; qc['approved_script_sha256']=approval['sha256']; qc['sources']=mix
    qc['saved_editor_revision']=state['revision'];qc['saved_timeline_sha256']=fingerprint(directory/f'06_edit/revisions/{state["revision"]:06d}.json')
    qc['style']=dict(profile_id=props['style']['profile_id'],version=props['style']['version'],transitions=[dict(scene=x['id'],transition=x['transition'],frames=x.get('transition_frames',0)) for x in props['scenes'] if x['transition']!='cut'],notes=props['style'].get('notes',[]))
    write_json(directory/'07_export/QC_REPORT.json',qc)
    textfile(directory/'07_export/QC_REPORT.md','# Technical QC passed\n\n'+json.dumps(qc,indent=2)+'\n\nHuman viewing/listening remains beneficial. No real audience-retention claims are made.')
    textfile(directory/'reports/COMPLETED_EDIT_RETENTION.md','# Completed edit evidence\n\n'+f'{len(props["scenes"])} static scenes ({sum(1 for x in props["scenes"] if x["transition"]!="cut")} with a crossfade/dip, style {props["style"]["profile_id"]}), {len(props["captions"])} SRT-grounded caption phrases; complete script text coverage; measured duration {props["durationInFrames"]/30:.2f}s.\n\n'+(directory/'03_storyboard/RETENTION_AUDIT.md').read_text(encoding='utf-8')+'\n\nNarrative ratings remain editorial judgments. Acoustic alignment, illustrated expressions and audience response were not machine-proven.')
    exports=current['data'].get('exports',[])+[dict(path=qc['path'],preview=str(preview.relative_to(STORE)).replace('\\','/'),job_id=jid,created=now(),qc='PASS',style=dict(profile_id=props['style']['profile_id'],version=props['style']['version']))]
    update_episode(eid,'COMPLETE',exports=exports,render_fingerprints=report['fingerprints'],error=None,message='Final exported under the single script authorization; not published')
    path=directory/f'.production/jobs/{jid}.json'
    state=read_json(path);state.update(status='COMPLETE',progress=1,stage='Export complete',updated=now());write_json(path,state)
    emit(directory,'render-'+str(jid),eid,'remotion','Export complete','render.completed','Final MP4 passed full decode and technical QC',file=final.relative_to(directory).as_posix())
    emit(directory,'render-'+str(jid),eid,'remotion','Export complete','job.completed','Final export ready; no publishing performed',status='COMPLETE')
    server.shutdown()

def job_eid(root):
    return read_json(root/'episode.json')['id']

def mix_path(plan,key):
    return plan['audio_measurements'][key]

def _sample_assets(out):
    """Disposable demonstration stills + silent audio for Preview Style when the episode has no assets yet."""
    from PIL import Image, ImageDraw
    sample = out / 'sample'
    sample.mkdir(parents=True, exist_ok=True)
    tones = [((38, 46, 58), (98, 108, 122)), ((52, 40, 48), (160, 120, 90)), ((22, 28, 36), (70, 80, 95))]
    for n, (dark, light) in enumerate(tones, 1):
        image = Image.new('RGB', (1080, 1920), dark)
        draw = ImageDraw.Draw(image)
        for y in range(1920):
            t = y / 1919
            draw.line([(0, y), (1080, y)], fill=tuple(int(dark[c] + (light[c] - dark[c]) * t * .6) for c in range(3)))
        draw.rectangle([240, 520, 840, 1380], outline=(241, 235, 221), width=10)
        draw.ellipse([430, 860, 650, 1080], fill=(255, 212, 59) if n == 2 else (125, 131, 139))
        image.save(sample / f'S00{n}.png')
    command(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '8', '-ar', '48000', sample / 'silence.wav'], timeout=60)
    return sample


def style_preview(eid, profile_ids):
    """Render ~5-8 s of real footage (or labelled samples) per profile. Never touches exports or episode settings."""
    if os.getenv('ODD_EPISODE_WORKER') != '1':
        raise ValueError('Style previews must execute inside the verified episode worker')
    from . import styles
    from .media import verify_timeline
    from urllib.parse import quote
    from functools import partial
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
    ep = episode(eid)
    directory = epdir(ep)
    out = directory / '06_edit/style_preview'
    out.mkdir(parents=True, exist_ok=True)
    report_path = directory / 'reports/ASSET_VALIDATION.json'
    report = read_json(report_path) if report_path.exists() else None
    real = bool(report and report.get('valid') and ep['data'].get('package') and ep['data'].get('approval'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(directory)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'

    def url(path):
        return base + quote(Path(path).relative_to(directory).as_posix(), safe='/')

    try:
        forced = {}
        notes = []
        if real:
            approved(ep)
            mix = mix_audio(eid, report, preview=True)
            narration = url(STORE / mix['narration'])
            instrumental = url(STORE / mix['instrumental'])
            plan = timeline(eid, report, style=styles.preview_style(ep, styles.FLOW_ID), write=False)
            scenes = plan['scenes']
            index = next((i for i, x in enumerate(scenes) if x['transition'] != 'cut'), None)
            if index is None:
                index = next((i for i in range(1, len(scenes))
                              if min(scenes[i - 1]['end'] - scenes[i - 1]['start'], scenes[i]['end'] - scenes[i]['start']) >= 24), None)
                if index is None:
                    raise ValueError('No scene boundary is long enough to demonstrate a transition')
                forced = {scenes[index]['id']: 'crossfade'}
                notes.append(f"This episode has no authored transition plan, so a demonstration crossfade was applied at {scenes[index]['id']} for the preview only.")
            boundary = scenes[index]['start']
            total = plan['durationInFrames']
            a = max(0, boundary - 75)
            b = min(total, a + 210)
            a = max(0, b - 210)

            def build(style):
                props = timeline(eid, report, style=style, extra_overrides=forced, write=False)
                return {**props, 'scenes': [{**x, 'image': url(STORE / x['image'])} for x in props['scenes']],
                        'narration': narration, 'instrumental': instrumental, 'render_range': [a, b - 1], 'sample': False}
            mode = 'episode'
        else:
            sample = _sample_assets(out)
            silence = url(sample / 'silence.wav')
            pk = [dict(scene_id='S001', narration_text='The door was locked from the inside', transition_in='cut', emphasis_phrase='', caption_style='default'),
                  dict(scene_id='S002', narration_text='The key was hanging outside', transition_in='crossfade', emphasis_phrase='hanging outside', caption_style='default', transition_reason='Gentle change of focus'),
                  dict(scene_id='S003', narration_text='Maro was gone', transition_in='cut', emphasis_phrase='', caption_style='default', transition_reason='Shock: hard cut'),
                  dict(scene_id='S004', narration_text='He wanted it found', transition_in='dip_to_dark', emphasis_phrase='found', caption_style='default', transition_reason='Dramatic pause before the reveal'),
                  dict(scene_id='S005', narration_text='You always look', transition_in='cut', emphasis_phrase='', caption_style='default')]
            spans = [(0, 70), (70, 130), (130, 170), (170, 215), (215, 240)]
            cues = [(4, 30, 'THE DOOR WAS LOCKED'), (32, 56, 'FROM THE INSIDE'), (72, 98, 'THE KEY WAS'), (100, 126, 'HANGING OUTSIDE'),
                    (132, 166, 'MARO WAS GONE'), (174, 196, 'HE WANTED'), (198, 212, 'IT FOUND'), (216, 238, 'YOU ALWAYS LOOK')]
            shots = [dict(id=p['scene_id'], start=a1, end=b1, image=url(sample / ('S%03d.png' % (n % 3 + 1))), caption_y=.46, motion='static', transition='cut')
                     for n, (p, (a1, b1)) in enumerate(zip(pk, spans))]
            offsets = []
            count = 0
            for _, _, text in cues:
                offsets.append(count)
                count += len(styles.clean_words(text))
            a, b = 0, 240
            mode = 'sample'
            notes.append('Your episode has no validated assets yet, so this preview uses DISPOSABLE SAMPLE stills and silence. It is labelled SAMPLE in the video.')

            def build(style):
                shot_copy = [dict(x) for x in shots]
                plan, tnotes = styles.resolve_transitions(pk, [x['end'] - x['start'] for x in shot_copy], style['profile'])
                for x, item in zip(shot_copy, plan):
                    x.update(transition=item['transition'], transition_frames=item['frames'], transition_reason=item['reason'])
                captions = [dict(start=c0, end=c1, text=t, y=.46, preset='quick_pop', timing='sample') for c0, c1, t in cues]
                styles.assign_caption_presets(captions, shot_copy, pk, offsets, style['profile'])
                props = dict(episode_id=ep['code'], width=1080, height=1920, fps=30, durationInFrames=240, scenes=shot_copy, captions=captions,
                             audioSources=['narration', 'instrumental'], style=styles.renderer_style(style, tnotes),
                             narration=silence, instrumental=silence, sample=True)
                verify_timeline(props)
                return {**props, 'render_range': [0, 239]}
        results = []
        for pid in profile_ids:
            style = styles.preview_style(ep, pid)
            props = build(style)
            target = out / f'{pid}.mp4'
            work = out / f'{pid}.work.mp4'
            work.unlink(missing_ok=True)
            render(props, work, True, 0, 0, name=f'style_{pid}', progress=False)
            info = probe(work)
            decoded(work)
            kinds = [x['codec_type'] for x in info['streams']]
            if kinds.count('video') != 1 or kinds.count('audio') != 1:
                raise ValueError('Style preview must contain one video and one audio stream')
            seconds = float(info['format']['duration'])
            if abs(seconds - (b - a) / 30) > .25:
                raise ValueError('Style preview duration mismatch')
            if target.exists():
                target.unlink()
            EpisodeWriter(directory).rename(work.relative_to(directory).as_posix(), target.relative_to(directory).as_posix())
            moving = [dict(scene=x['id'], transition=x['transition'], frames=x.get('transition_frames', 0)) for x in props['scenes'] if x['transition'] != 'cut']
            results.append(dict(profile_id=pid, label=style['profile']['label'], version=style['version'], file=target.relative_to(STORE).as_posix(),
                                seconds=round(seconds, 2), transitions=moving, presets=sorted({c['preset'] for c in props['captions'] if a <= c['start'] < b}),
                                pinned_by_episode=style.get('pinned_here', False)))
        meta = dict(created=now(), mode=mode, window_frames=[a, b], window_seconds=round((b - a) / 30, 2), demo_transition=forced, notes=notes, profiles=results)
        write_json(out / 'preview.json', meta)
        return meta
    finally:
        server.shutdown()


def secure_validate(eid):
    ep=episode(eid);directory=epdir(ep)
    from .snapshots import bootstrap,validate,pin_imported_music
    if not (directory/'.production/provenance.json').exists():bootstrap(directory)
    validate(directory)
    jobid='validate-'+__import__('uuid').uuid4().hex
    with episode_lock(directory,'media'):
        result=isolation.launch(directory,[sys.executable,'-B',str(ROOT/'scripts/production_worker.py'),'validate',str(eid)],jobid,timeout=120)
        if result['returncode']:raise ValueError('Isolated asset validation failed: '+(result['stderr'] or result['stdout'])[-2000:])
        report=read_json(directory/'reports/ASSET_VALIDATION.json')
        if report['valid']:
            music=STORE/report['sources']['music']['path']
            pin_imported_music(directory,music,ep['data'].get('music_rights',{}).get('evidence',''))
    return report

def run_isolated_render(job):
    eid=job['episode_id'];ep=episode(eid);directory=epdir(ep)
    writer=EpisodeWriter(directory)
    relative=f'.production/jobs/{job["id"]}.json'
    if writer.path(relative).exists():job={**read_json(writer.path(relative)),**job}
    writer.json(relative,job)
    with episode_lock(directory,'media',blocking=False):
        result=isolation.launch(directory,[sys.executable,'-B',str(ROOT/'scripts/production_worker.py'),'draft' if job['kind']=='draft' else 'render',relative],
                                'render-'+str(job['id']),network=True,timeout=1800)
    state=read_json(directory/relative)
    if result['returncode'] or state.get('status')!='COMPLETE':
        raise ValueError('Isolated render failed: '+(state.get('error') or result['stderr'] or result['stdout'])[-2000:])
    with db() as c:
        c.execute('UPDATE jobs SET status=?,progress=?,stage=?,updated=? WHERE id=?',(state['status'],state['progress'],state['stage'],now(),job['id']))

def scan():
    with db() as c:
        ids=[r['id'] for r in c.execute("SELECT id FROM episodes WHERE status IN ('AWAITING_ASSETS','ASSETS_BLOCKED')")]
    for eid in ids:
        try:
            report=secure_validate(eid)
            ep=episode(eid)
            if report['valid']:
                if (epdir(ep)/'06_edit/editor_state.json').exists():
                    from .editor import needs_rebuild
                    stale=needs_rebuild(eid,report)
                    update_episode(eid,'EDIT_STALE' if stale else 'EDIT_READY',error=None,message='Assets or style changed. Use Rebuild Draft explicitly; previous revisions are preserved.' if stale else 'Saved draft ready in Live Editor')
                else:enqueue(eid)
            elif ep['data'].get('asset_errors')!=report['errors']:
                update_episode(eid,'ASSETS_BLOCKED',asset_errors=report['errors'])
        except Exception as exc:
            ep=episode(eid)
            if ep['data'].get('error')!=str(exc):
                update_episode(eid,'ASSETS_BLOCKED',error=str(exc))

def loop():
    # Exactly one render worker. SQLite active-job index prevents duplicate per-episode work.
    last_scan=0
    while not stop.is_set():
        try:
            if time.monotonic()-last_scan>10:
                scan(); last_scan=time.monotonic()
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                job=c.execute("SELECT * FROM jobs WHERE status='QUEUED' ORDER BY id LIMIT 1").fetchone()
                if job:
                    c.execute("UPDATE jobs SET status='RUNNING',updated=? WHERE id=?",(now(),job['id']))
            if job:
                try:
                    run_isolated_render(dict(job))
                except Exception as exc:
                    with db() as c:
                        c.execute("UPDATE jobs SET status='FAILED',error=?,stage='Blocked',updated=? WHERE id=?",(str(exc),now(),job['id']))
                    update_episode(job['episode_id'],'FAILED',error=str(exc))
                    emit(epdir(episode(job['episode_id'])),'render-'+str(job['id']),job['episode_id'],'deterministic' if job['kind']=='draft' else 'remotion','Blocked','ai.failed','Production job failed. Check asset validation, isolation and media runtime before retrying.',status='FAILED')
        except Exception:
            import logging
            logging.exception('Queue loop failed; worker will retry polling')
        stop.wait(2)

def start_worker():
    stop.clear()
    from .providers import cleanup_private_job_homes
    with db() as c:registered=[r['id'] for r in c.execute('SELECT id FROM episodes')]
    for eid in registered:cleanup_private_job_homes(epdir(episode(eid)))
    for category in ('_ideas','_provider_tests'):
        directory=STORE/'episodes'/category
        if directory.exists():
            for root in directory.iterdir():
                if root.is_dir():cleanup_private_job_homes(root)
    with db() as c:
        c.execute("UPDATE jobs SET status='QUEUED',stage='Resuming after interruption',updated=? WHERE status='RUNNING'",(now(),))
        interrupted=[r['id'] for r in c.execute("SELECT id FROM runs WHERE status IN ('RUNNING','QUEUED')")]
    from .creative import fail_run
    for runid in interrupted:fail_run(runid,'INTERRUPTED: Retry explicitly; no model call is replayed silently after restart')
    thread=threading.Thread(target=loop,name='odd-frame-single-render-worker',daemon=True)
    thread.start()
    return thread
