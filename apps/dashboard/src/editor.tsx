import React, {memo, useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {Player, type PlayerRef} from '@remotion/player';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useParams} from '@tanstack/react-router';
import {OddFrameReel, type ReelProps, type Caption} from '../../../video/remotion/src/composition';
import {api} from './api';
import './studio.css';

type Timeline=ReelProps & {audio:NonNullable<ReelProps['audio']>};
type Draft={timeline:Timeline;baseline:Timeline;state:{revision:number;updated:string};waveforms:{narration:number[];music:number[]};title:string;revisions:number[]};
type Selection={kind:'caption'|'scene';index:number}|{kind:'narration'|'music';index:0};
type History={past:Timeline[];present:Timeline;future:Timeline[]};
const url=(path:string)=>'/api/media/'+path.split('/').map(encodeURIComponent).join('/');
const presets=['quick_pop','wave_reveal','glow_pop','smooth_replace','immediate_impact','soft_fade'];
const clone=<T,>(v:T):T=>structuredClone(v);

const AudioLevels=memo(function AudioLevels({player,waves,audio,frames,audition,solo}:{player:React.RefObject<PlayerRef|null>;waves:Draft['waveforms'];audio:Timeline['audio'];frames:number;audition:{narration_muted:boolean;music_muted:boolean};solo:'narration'|'music'|null}){
  const [frame,setFrame]=useState(0);
  useEffect(()=>{const p=player.current;if(!p)return;const update=(e:{detail:{frame:number}})=>setFrame(e.detail.frame);p.addEventListener('timeupdate',update);p.addEventListener('seeked',update);return()=>{p.removeEventListener('timeupdate',update);p.removeEventListener('seeked',update)}},[player]);
  return <div className="audio-levels"><small>Decoded source peak at playhead (before final mastering)</small>{(['narration','music'] as const).map(role=>{
    const faded=role==='music'?Math.min(1,audio.fade_in?frame/audio.fade_in:1,audio.fade_out?(frames-1-frame)/audio.fade_out:1)*(1-audio.ducking*(audio.envelope[frame]||0)):1;
    const muted=audition[role==='music'?'music_muted':'narration_muted']||(solo&&solo!==role);
    const peak=muted?0:(waves[role][Math.floor(frame/30*100)]||0)*audio[role==='music'?'music_gain':'narration_gain']*faded;
    const db=peak>0?20*Math.log10(peak):-60;
    return <label key={role}>{role}<meter min={-60} max={0} value={Math.max(-60,db)}/><output>{peak>0?db.toFixed(1)+' dBFS':'−∞'}</output></label>
  })}</div>
});

const Wave=memo(function Wave({peaks}:{peaks:number[]}){
  const points=useMemo(()=>{
    const step=Math.max(1,Math.floor(peaks.length/700));
    return peaks.filter((_,i)=>i%step===0).map((p,i)=>`${i},${24-p*23}`).join(' ');
  },[peaks]);
  const width=Math.ceil(peaks.length/Math.max(1,Math.floor(peaks.length/700)));
  return <svg className="waveform" viewBox={`0 0 ${width} 48`} preserveAspectRatio="none" aria-label="Decoded audio waveform"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="1"/><polyline points={points} fill="none" stroke="currentColor" strokeWidth="1" transform="translate(0 48) scale(1 -1)"/></svg>
});

// Frame events update only this small timeline component; dashboard queries never drive playback.
const TimelineTracks=memo(function TimelineTracks({timeline,waves,player,select,selection}:{timeline:Timeline;waves:Draft['waveforms'];player:React.RefObject<PlayerRef|null>;select:(s:Selection)=>void;selection:Selection}){
  const [frame,setFrame]=useState(0);
  useEffect(()=>{const p=player.current;if(!p)return;const update=(e:{detail:{frame:number}})=>setFrame(e.detail.frame);p.addEventListener('frameupdate',update);return()=>p.removeEventListener('frameupdate',update)},[player]);
  const total=timeline.durationInFrames,position=(f:number)=>`${f/total*100}%`;
  const seek=(e:React.MouseEvent<HTMLElement>)=>{const rect=e.currentTarget.getBoundingClientRect();player.current?.seekTo(Math.max(0,Math.min(total-1,Math.round((e.clientX-rect.left)/rect.width*total))))};
  const segments=(kind:'scene'|'caption')=>(kind==='scene'?timeline.scenes:timeline.captions).map((item,i)=><button key={i} title={kind==='scene'?timeline.scenes[i].id:timeline.captions[i].text} className={`timeline-clip ${selection.kind===kind&&selection.index===i?'selected':''}`} style={{left:position(item.start),width:position(item.end-item.start)}} onClick={e=>{e.stopPropagation();select({kind,index:i});player.current?.seekTo(item.start)}}>
    {kind==='scene'?<><img src={url(timeline.scenes[i].image)} loading="lazy" alt=""/><span>{timeline.scenes[i].id} {timeline.scenes[i].transition!=='cut'?'◇':''}</span></>:timeline.captions[i].text}
  </button>);
  return <section className="timeline-panel" aria-label="Four-track timeline"><div className="studio-row"><h2>Timeline</h2><output>{frame} / {total} frames · {(frame/30).toFixed(2)}s · 30 fps</output></div>
    <div className="timeline-scroll"><div className="timeline-grid"><div className="track-label">Time</div><div className="time-ruler" onClick={seek}>{Array.from({length:Math.ceil(total/150)},(_,i)=><span key={i} style={{left:position(i*150)}}>{i*5}s</span>)}</div>
    <div className="track-label">STILL IMAGES</div><div className="track-track images-track" onClick={seek}>{segments('scene')}</div>
    <div className="track-label">ANIMATED CAPTIONS</div><div className="track-track captions-track" onClick={seek}>{segments('caption')}</div>
    <button className="track-label" onClick={()=>select({kind:'narration',index:0})}>NARRATION</button><div className="track-track narration-track" onClick={seek}><Wave peaks={waves.narration}/></div>
    <button className="track-label" onClick={()=>select({kind:'music',index:0})}>SIGNATURE INSTRUMENTAL</button><div className="track-track music-track" onClick={seek}><Wave peaks={waves.music}/></div>
    <div className="playhead-lane"><div className="timeline-playhead" style={{left:position(frame)}}/>{timeline.scenes.slice(1).map(s=><div className="scene-boundary" key={s.id} style={{left:position(s.start)}}/>)}</div></div></div>
    <input aria-label="Timeline playhead" type="range" min={0} max={total-1} value={frame} onChange={e=>player.current?.seekTo(Number(e.target.value))}/>
  </section>
});

function NumberControl({label,value,min,max,step=1,onChange,disabled=false}:{label:string;value:number;min:number;max:number;step?:number;disabled?:boolean;onChange:(n:number)=>void}){return <label>{label}<div className="studio-row"><input aria-label={label} disabled={disabled} type="range" min={min} max={max} step={step} value={value} onChange={e=>onChange(Number(e.target.value))}/><output>{Number(value.toFixed(2))}</output></div></label>}

function LoadedEditor({draft,eid}:{draft:Draft;eid:string}){
  const client=useQueryClient(),player=useRef<PlayerRef>(null);
  const [history,setHistory]=useState<History>({past:[],present:draft.timeline,future:[]});
  const timeline=history.present;
  const [revision,setRevision]=useState(draft.state.revision),[revisions,setRevisions]=useState(draft.revisions),[saved,setSaved]=useState(JSON.stringify(draft.timeline)),[message,setMessage]=useState('Draft ready for review'),[error,setError]=useState(''),[saving,setSaving]=useState(false),[rate,setRate]=useState(1),[selection,setSelection]=useState<Selection>({kind:'scene',index:0});
  const [audition,setAudition]=useState({narration_muted:false,music_muted:false}),[solo,setSolo]=useState<'narration'|'music'|null>(null),[buffering,setBuffering]=useState(false);
  const savingRef=useRef(false),timelineRef=useRef(timeline);timelineRef.current=timeline;
  const {mutateAsync:persist}=useMutation({mutationFn:(payload:unknown)=>api(`/episodes/${eid}/editor`,'PUT',payload)});
  const dirty=JSON.stringify(timeline)!==saved;
  const mutate=useCallback((change:(next:Timeline)=>void)=>{setError('');setHistory(h=>{const next=clone(h.present);change(next);return {past:[...h.past,h.present].slice(-80),present:next,future:[]}})},[]);
  const undo=()=>setHistory(h=>h.past.length?{past:h.past.slice(0,-1),present:h.past.at(-1)!,future:[h.present,...h.future]}:h);
  const redo=()=>setHistory(h=>h.future.length?{past:[...h.past,h.present],present:h.future[0],future:h.future.slice(1)}:h);
  const save=useCallback(async()=>{
    if(savingRef.current)return null;
    savingRef.current=true;setSaving(true);setError('');const snapshot=timelineRef.current;
    try{
      const audio=snapshot.audio;
      const result=await persist({revision,
        scenes:snapshot.scenes.map(({id,transition,transition_frames=0})=>({id,transition,transition_frames})),
        captions:snapshot.captions.map(({text,start,end,y,preset,emphasis='none',enter_frames=5,exit_frames=0,glow=true,size=1,glow_strength=1})=>({text,start,end,y,preset,emphasis,enter_frames,exit_frames,glow,size,glow_strength})),
        audio:{narration_gain:audio.narration_gain,music_gain:audio.music_gain,fade_in:audio.fade_in,fade_out:audio.fade_out,ducking:audio.ducking}});
      setRevision(result.revision);setRevisions(r=>[...r,result.revision]);setSaved(JSON.stringify(snapshot));setMessage(`Saved revision ${result.revision}`);
      client.setQueryData<Draft>(['editor',eid],old=>old?{...old,timeline:snapshot,state:{revision:result.revision,updated:new Date().toISOString()},revisions:[...old.revisions,result.revision]}:old);
      return result.revision as number;
    }catch(e){setError((e as Error).message);return null}finally{savingRef.current=false;setSaving(false)}
  },[eid,revision,persist]);
  useEffect(()=>{if(!dirty||error)return;const timer=setTimeout(()=>void save(),1200);return()=>clearTimeout(timer)},[timeline,dirty,error,save]);
  useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[dirty]);
  useEffect(()=>{const p=player.current;if(!p)return;const waiting=()=>setBuffering(true),ready=()=>setBuffering(false);p.addEventListener('waiting',waiting);p.addEventListener('resume',ready);return()=>{p.removeEventListener('waiting',waiting);p.removeEventListener('resume',ready)}},[]);
  const props=useMemo(()=>({...timeline,scenes:timeline.scenes.map(s=>({...s,image:url(s.image)})),narration:url(timeline.narration),instrumental:url(timeline.instrumental),audition:{narration_muted:audition.narration_muted||solo==='music',music_muted:audition.music_muted||solo==='narration'}}),[timeline,audition,solo]);
  // Warm image decoding once. Img itself tracks buffering; assets are stable between control changes.
  useEffect(()=>{const images=timeline.scenes.slice(0,4).map(s=>{const image=new Image();image.src=url(s.image);return image});return()=>{images.forEach(i=>i.src='')}},[timeline.scenes[0]?.image]);
  const caption=selection.kind==='caption'?timeline.captions[selection.index]:null;
  const scene=selection.kind==='scene'?timeline.scenes[selection.index]:null;
  function changeCaption(patch:Partial<Caption>){mutate(next=>Object.assign(next.captions[selection.index],patch))}
  async function render(){const current=dirty?await save():revision;if(!current)return;try{await api(`/episodes/${eid}/editor/render`,'POST',{revision:current});setMessage(`Final render queued from revision ${current}`);client.invalidateQueries({queryKey:['activity']})}catch(e){setError((e as Error).message)}}
  async function rebuild(){
    try{
      if(dirty&&!await save())return;
      await api(`/episodes/${eid}/editor/rebuild`,'POST');setMessage('Draft rebuild queued. Follow AI Activity, then reload the completed draft.')
    }
    catch(e){setError((e as Error).message)}
  }
  return <main className="live-studio"><header className="studio-header"><div><a href="/">← Dashboard</a><h1>{draft.title}</h1><span>Live Editor · Revision {revision} · {dirty?'Unsaved changes':'Saved'}</span></div><div className="studio-actions"><button disabled={!history.past.length} onClick={undo}>Undo</button><button disabled={!history.future.length} onClick={redo}>Redo</button><button disabled={saving||!dirty} onClick={()=>void save()}>Save Edit</button><button onClick={()=>{player.current?.seekTo(Math.max(0,selection.kind==='caption'?caption!.start:selection.kind==='scene'?scene!.start:0));void player.current?.play()}}>Quick Preview</button><button className="primary" disabled={saving} onClick={()=>void render()}>Render Final Video</button></div></header>
    <div className="studio-notice" role={error?'alert':'status'}>{error|| (buffering?'Buffering assets…':saving?'Saving episode-local edit…':message)}</div>
    <details className="draft-rebuild"><summary>Draft sources and pinned style</summary><p>{timeline.style?.profile_id} · {timeline.style?.version}. Classic episodes retain their original caption and transition options. Use the dashboard’s explicit profile adoption before rebuilding if you want Cinematic Flow.</p><p>After replacing assets or changing preparation settings, rebuild the automatic draft. Saved revisions and prior prepared audio remain available.</p><button onClick={()=>void rebuild()}>Rebuild Draft · preserve history</button></details>
    <label className="revision-selector">Revision history <select aria-label="Restore revision" defaultValue="" onChange={async e=>{if(!e.target.value)return;try{const prior=await api(`/episodes/${eid}/editor/revisions/${e.target.value}`);mutate(next=>Object.assign(next,prior));setError('');setMessage('Historical revision restored as an editable change; autosave creates a new revision.')}catch(err){setError((err as Error).message)}e.target.value=''}}><option value="">Restore a saved revision…</option>{Array.from(new Set(revisions)).sort((a,b)=>b-a).map(r=><option key={r} value={r}>Revision {r}</option>)}</select></label>
    <div className="studio-workspace"><section className="player-panel"><Player ref={player} component={OddFrameReel} inputProps={props} durationInFrames={timeline.durationInFrames} compositionWidth={1080} compositionHeight={1920} fps={30} controls playbackRate={rate} showPlaybackRateControl showVolumeControls allowFullscreen style={{height:'100%',maxHeight:'58vh',aspectRatio:'9/16'}} errorFallback={({error:playerError})=><div role="alert">Preview error: {playerError.message}</div>}/>
      <div className="studio-row transport"><button onClick={()=>player.current?.seekTo(Math.max(0,(player.current?.getCurrentFrame()||0)-1))}>← Frame</button><button onClick={()=>player.current?.toggle()}>Play / Pause</button><button onClick={()=>player.current?.seekTo(Math.min(timeline.durationInFrames-1,(player.current?.getCurrentFrame()||0)+1))}>Frame →</button><select aria-label="Playback speed" value={rate} onChange={e=>setRate(Number(e.target.value))}>{[.5,.75,1,1.25,1.5,2].map(r=><option key={r} value={r}>{r}×</option>)}</select></div></section>
      <aside className="studio-inspector"><h2>{caption?'Caption':scene?`Scene ${scene.id}`:'Audio mixer'}</h2>
        {caption&&<><label>Caption words<textarea aria-label="Caption words" value={caption.text} onChange={e=>changeCaption({text:e.target.value})}/><small>Preserve approved words and phrase grouping.</small></label><label>Animation<select aria-label="Caption animation" value={caption.preset} onChange={e=>changeCaption({preset:e.target.value as Caption['preset']})}>{(timeline.style?.renderer==='cinematic'?presets:['quick_pop']).map(p=><option key={p} value={p}>{p.replaceAll('_',' ')}</option>)}</select></label>
          <NumberControl label="Caption size" value={caption.size??1} min={.8} max={1} step={.01} onChange={size=>changeCaption({size})}/><NumberControl label="Caption position" value={caption.y} min={.17} max={.73} step={.01} onChange={y=>changeCaption({y})}/><fieldset disabled={timeline.style?.renderer!=='cinematic'}><NumberControl label="Glow strength" value={caption.glow_strength??1} min={0} max={2} step={.05} onChange={glow_strength=>changeCaption({glow_strength})}/><label>Glow emphasis<select aria-label="Glow emphasis" value={caption.emphasis||'none'} onChange={e=>changeCaption({emphasis:e.target.value as 'none'|'gold'})}><option value="none">White</option><option value="gold">Gold</option></select></label><NumberControl label="Animation duration (frames)" value={caption.enter_frames??5} min={0} max={Math.min(30,caption.end-caption.start)} onChange={enter_frames=>changeCaption({enter_frames})}/>
          </fieldset>{timeline.style?.renderer!=='cinematic'&&<small>Classic keeps its fixed Quick Pop animation and outline. Cinematic glow controls require explicit style adoption.</small>}<label>Phrase start (frame)<input aria-label="Phrase start" type="number" value={caption.start} onChange={e=>changeCaption({start:Number(e.target.value)})}/></label><label>Phrase end (frame)<input aria-label="Phrase end" type="number" value={caption.end} onChange={e=>changeCaption({end:Number(e.target.value)})}/></label><small>Timing corrections are validated within ±2 frames of the supplied SRT.</small></>}
        {scene&&<><img className="inspector-still" src={url(scene.image)} alt={scene.id}/><p>{scene.start}–{scene.end} frames · Static 2D still</p><label>Transition<select aria-label="Scene transition" value={scene.transition} disabled={selection.index===0} onChange={e=>mutate(next=>Object.assign(next.scenes[selection.index],{transition:e.target.value,transition_frames:e.target.value==='cut'?0:8}))}>{(timeline.style?.allowed_transitions||['cut']).map(t=><option key={t} value={t}>{t.replaceAll('_',' ')}</option>)}</select></label><NumberControl label="Transition frames" value={scene.transition_frames||0} min={scene.transition==='cut'?0:1} max={scene.transition==='cut'?0:30} onChange={transition_frames=>mutate(next=>{next.scenes[selection.index].transition_frames=transition_frames})}/></>}
        {(scene||caption)&&<button onClick={()=>{const original=draft.baseline;mutate(next=>{if(selection.kind==='caption')next.captions[selection.index]=clone(original.captions[selection.index]);else if(selection.kind==='scene')next.scenes[selection.index]=clone(original.scenes[selection.index])})}}>Reset Selected Effect</button>}
        <h2>Two-channel mixer</h2><AudioLevels player={player} waves={draft.waveforms} audio={timeline.audio} frames={timeline.durationInFrames} audition={audition} solo={solo}/>{(['narration','music'] as const).map(role=><section className="mixer-channel" key={role}><strong>{role==='music'?'Signature instrumental':'Narration'}</strong><NumberControl label={`${role==='music'?'Music':'Narration'} gain`} value={timeline.audio[role==='music'?'music_gain':'narration_gain']} min={role==='music'?0:.25} max={1} step={.01} onChange={v=>mutate(next=>{next.audio[role==='music'?'music_gain':'narration_gain']=v})}/><div className="studio-row"><button aria-pressed={audition[role==='music'?'music_muted':'narration_muted']} onClick={()=>setAudition(a=>({...a,[role==='music'?'music_muted':'narration_muted']:!a[role==='music'?'music_muted':'narration_muted']}))}>Mute</button><button aria-pressed={solo===role} onClick={()=>setSolo(s=>s===role?null:role)}>Solo</button></div><Wave peaks={draft.waveforms[role]}/></section>)}
        <NumberControl label="Music fade in (frames)" value={timeline.audio.fade_in} min={0} max={90} onChange={v=>mutate(n=>{n.audio.fade_in=v})}/><NumberControl label="Music fade out (frames)" value={timeline.audio.fade_out} min={0} max={90} onChange={v=>mutate(n=>{n.audio.fade_out=v})}/><NumberControl label="Additional narration ducking" value={timeline.audio.ducking} min={0} max={.8} step={.05} onChange={v=>mutate(n=>{n.audio.ducking=v})}/><small>Measured ducking is already baked into the continuous instrumental bed. These controls add frame-based adjustments. Mute and solo affect audition only. Final mastering may change overall loudness.</small><a href="/help">Audio and job progress help</a>
      </aside></div>
    <TimelineTracks timeline={timeline} waves={draft.waveforms} player={player} selection={selection} select={setSelection}/>
  </main>
}

export function LiveEditor(){
  const {episodeId:eid}=useParams({from:'/episodes/$episodeId/editor'});
  const [actionMessage,setActionMessage]=useState('');
  const query=useQuery<Draft>({queryKey:['editor',eid],queryFn:()=>api(`/episodes/${eid}/editor`),retry:false,refetchOnWindowFocus:false});
  async function prepareDraft(rebuild=false){
    try{
      await api(`/episodes/${eid}/editor/${rebuild?'rebuild':'prepare'}`,'POST');
      setActionMessage('Draft preparation queued. Follow AI Activity, then open the completed draft.');
      await query.refetch();
    }catch(e){setActionMessage((e as Error).message)}
  }
  if(query.isPending)return <main className="progress-help"><a href="/">← Dashboard</a><p>Loading the saved editable draft…</p></main>;
  if(query.error)return <main className="progress-help"><a href="/">← Dashboard</a><h1>Draft is not ready</h1><p role="alert">{query.error.message}</p><button onClick={()=>void prepareDraft()}>Prepare automatic draft</button>{query.error.message.toLowerCase().includes('rebuild')&&<button onClick={()=>void prepareDraft(true)}>Retry draft rebuild</button>}<p role="status">{actionMessage||'Follow preparation in AI Activity. Open this editor after the draft is ready.'}</p></main>;
  return <LoadedEditor key={eid} draft={query.data} eid={eid}/>;
}
