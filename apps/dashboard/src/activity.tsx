import {Sheet,SheetContent,SheetTrigger,SheetHeader,SheetTitle,SheetDescription} from '@/components/ui/sheet';
import {Button} from '@/components/ui/button';
import {useEffect, useState} from 'react';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {api} from './api';
import {Activity, ChevronRight} from 'lucide-react';
import {Paged} from './paging';
type ActivityEvent = {event_id:string; timestamp:string; message:string; type:string; completed?:number; total?:number; file?:string;retry_of?:string};
type Job = {job_id:string; episode_id:number|null; provider:string; status:string; task:string; stage:string; created:string; started_at?:string; finished_at?:string; events:ActivityEvent[]; error?:string; cancellable:boolean; retryable:boolean};
const running=(j:Job)=>['QUEUED','RUNNING'].includes(j.status);

export function ActivityMonitor({embedded=false}:{embedded?:boolean}={}){
  const client=useQueryClient();
  const {data:jobs=[]}=useQuery<Job[]>({queryKey:['activity'],queryFn:({signal})=>api('/activity','GET',undefined,signal),refetchInterval:15000});
  const [open,setOpen]=useState(false),[filter,setFilter]=useState('all'),[connection,setConnection]=useState('Connecting'),[error,setError]=useState(''),[tick,setTick]=useState(Date.now());
  useEffect(()=>{
    if(embedded)return;const source=new EventSource('/api/activity/stream');let refresh:ReturnType<typeof setTimeout>|undefined;
    const update=()=>{if(!refresh)refresh=setTimeout(()=>{client.invalidateQueries({queryKey:['activity']});refresh=undefined},150)};
    source.addEventListener('activity',update);source.addEventListener('reset',update);
    source.onopen=()=>{setConnection('Live');update()};source.onerror=()=>setConnection('Reconnecting');
    return ()=>{source.close();clearTimeout(refresh)};
  },[client,embedded]);
  useEffect(()=>{const timer=setInterval(()=>setTick(Date.now()),1000);return()=>clearInterval(timer)},[]);
  const active=jobs.filter(running),visible=jobs.filter(j=>filter==='all'||String(j.episode_id)===filter);
  const connectionDetail=connection==='Reconnecting'?'Reconnecting to live updates. Saved job status remains available.':connection==='Live'?'Connected to live job updates.':'Connecting to live job updates.';
  const taskLabel=active.length?`${active.length} running job${active.length>1?'s':''}`:'AI Activity';
  async function action(job:Job,kind:'cancel'|'retry'){
    try{setError('');await api(`/runs/${job.job_id}/${kind}`,'POST');await client.invalidateQueries({queryKey:['activity']})}
    catch(e){setError((e as Error).message)}
  }
  const trigger=<Button className="activity-launch" data-connection={connection.toLowerCase()} onClick={()=>setOpen(!open)} aria-label={`${taskLabel}, ${connection}`} aria-expanded={open} aria-controls="ai-activity-panel" title={connectionDetail}>
    <span className="activity-launch-icon"><Activity size={17} aria-hidden="true"/></span>
    <span className="activity-launch-copy"><strong>{taskLabel}</strong><small><span className="activity-connection-dot"/>{connection}</small></span>
    <ChevronRight size={14} className="activity-launch-chevron" aria-hidden="true"/>
  </Button>;
  const content=<><p>{embedded?"Saved jobs and verified events. The header control streams live updates.":connectionDetail} Status is saved on this station.</p><a href="/help">Understanding AI Job Progress</a>
      <label>Jobs <select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All Jobs</option>{Array.from(new Set(jobs.map(j=>j.episode_id))).map(id=><option key={String(id)} value={String(id)}>{id?`OF_R${String(id).padStart(3,'0')}`:'Story ideas / provider tests'}</option>)}</select></label>
      {error&&<p role="alert">{error}</p>}{!visible.length&&<p>No recorded jobs yet. Generate ideas or open an episode to begin.</p>}
      <Paged items={visible} size={5} label="jobs" resetKey={filter} empty={<></>} getText={j=>`${j.job_id} ${j.episode_id??""} ${j.task} ${j.provider} ${j.stage} ${j.status} ${j.error||""}`}>{rows=>rows.map(job=>{
        const last=job.events.at(-1),elapsed=Math.max(0,Math.floor(((job.finished_at?Date.parse(job.finished_at):tick)-Date.parse(job.started_at||job.created))/1000));
        const count=[...job.events].reverse().find(e=>e.total!==undefined&&e.completed!==undefined);
        const silent=running(job)&&job.status!=='QUEUED'&&tick-Date.parse(last?.timestamp||job.created)>90000;
        const files=Array.from(new Set(job.events.filter(e=>e.file).map(e=>e.file!)));
        return <section className="activity-job" key={job.job_id}><div className="studio-row"><strong>{job.episode_id?`OF_R${String(job.episode_id).padStart(3,'0')}`:job.task==='connection_test'?'Provider diagnostic':'Story ideas'} · {job.task}</strong><span>{job.status.replaceAll('_',' ')}</span></div>
          <p>{job.provider} · {job.stage} · {Math.floor(elapsed/60)}m {elapsed%60}s</p><small>Job {job.job_id} · Started {job.started_at?new Date(job.started_at).toLocaleString():'not started'}</small>
          {count&&count.total!>0&&<p>{count.completed} of {count.total} {count.type==='render.progress'?'frames rendered':'items validated'}</p>}
          {running(job)&&<p className="live-stage"><span className="live-dot"/>{silent?'AI generation is still running. No detailed progress events are currently available.':last?.message||'Queued; waiting for an available worker.'}</p>}
          {job.error&&<p role="alert">{job.error}</p>}
          <details><summary>Milestones, files and recent activity</summary><ul>{job.events.filter(e=>['skills.validated','stage.completed','file.saved','render.completed','job.completed'].includes(e.type)).map(e=><li key={e.event_id}>{e.message}{e.file?' · '+e.file:''}</li>)}</ul>
            <ol className="activity-log">{job.events.slice(-80).map(e=><li key={e.event_id}><time>{new Date(e.timestamp).toLocaleTimeString()}</time> {e.message}{e.retry_of?' · Retry of '+e.retry_of:''}</li>)}</ol>
            <p>Last event: {last?new Date(last.timestamp).toLocaleString():'Waiting for first event'}</p><p>Generated files: {files.length?files.join(', '):'None verified yet'}</p>
          </details>
          {job.cancellable&&<Button onClick={()=>action(job,'cancel')}>Cancel generation</Button>}{job.retryable&&<Button onClick={()=>action(job,'retry')}>Retry as new job</Button>}
          {!running(job)&&<p className="next-action">{job.status==='AWAITING_MANUAL'?'Next: download the complete request and import your structured response in the dashboard.':last?.message||'Open the episode workspace for the next action.'}</p>}
          {job.task==='draft'&&job.status==='COMPLETE'&&job.episode_id&&<a className="open-live-editor" href="/">Open Edit Studio → Remotion Studio</a>}
        </section>
      })}</Paged></>;
  return embedded?<section className="panel activity-panel"><h2>Saved activity</h2>{content}</section>:<Sheet open={open} onOpenChange={setOpen}><SheetTrigger asChild>{trigger}</SheetTrigger><SheetContent id="ai-activity-panel" className="activity-panel w-[min(640px,96vw)] sm:max-w-[640px] overflow-y-auto p-6"><SheetHeader><SheetTitle>AI Activity</SheetTitle><SheetDescription>Actual provider events and saved job states.</SheetDescription></SheetHeader>{content}</SheetContent></Sheet>;

}

export function ProgressHelp(){return <main className="progress-help"><a href="/">← Dashboard</a><h1>Understanding AI Job Progress</h1><p>The activity button stays available as you move between pages. Choose All Jobs or one episode. Each job has its own provider, ID, history and output files.</p>
  <dl>{[
    ['Queued / Starting','Your task is saved and waiting for a free worker. A queued task is not yet using the AI provider.'],
    ['Loading skills / Preparing request','The station reads and checks all four complete pinned creative documents, the master prompt and stage instructions.'],
    ['Waiting for provider / Generating','The authorized CLI is running. Large creative packages can take several minutes. Some providers send only a few status events, so elapsed time is shown without an invented percentage.'],
    ['Validating / Saving','The response is checked against its schema and story coverage before any generated files are recorded as complete.'],
    ['Waiting for script approval','Read the draft in Script Studio. Approve once to freeze the wording and start episode preparation. No AI is running while it waits for you.'],
    ['Waiting for uploaded assets','Add your Flow still images, narration and SRT in Asset Manager. The pinned instrumental must also be available.'],
    ['Auto Edit / Ready for review','The station aligns scenes and captions to your supplied subtitles and measures the two audio sources. Then open it in the official Remotion Studio (Edit Studio page) to review and adjust it without rendering an MP4.'],
    ['Editing in Remotion Studio','In Edit Studio click Open in Remotion Studio. When the panel says Remotion Studio Ready, open the editor. Adjust props or timeline, your changes are saved to the episode, then use Render final MP4 from this Studio project.'],
    ['Rendering / Running QC','Remotion renders the saved timeline. Frame counts come from the renderer. FFmpeg then checks the actual encoded output. This is separate from AI generation.'],
    ['Completed / Generated files','Expand a job to see verified filenames. Open the episode workspace to download public creative documents, or Exports for final videos. Private AI request files are not public media.'],
    ['Failed / Retry','Check the episode error and provider status in Settings. Fix missing assets, expired login or usage limits, then use Retry where offered. A retry creates a new job and does not rewrite approved narration.'],
    ['Cancelled / Cancel','Cancel is offered for active AI runs supported by the backend. It terminates the isolated process tree. Render cancellation is not offered here.'],
    ['Disconnected / Reconnecting','Recent events and status remain on disk. The browser reconnects and replays events; refreshing restores the current job. A long silent provider does not imply a completed scene.'],
    ['Audio preview and final mastering','The player uses the measured normalized narration and ducked instrumental separately. Live gain, fades and additional ducking use the same frame controls as export. Audition mute and solo are temporary. Final FFmpeg loudness and true-peak mastering can change the overall playback level. Listen to and validate the final file.'],
  ].map(([term,text])=><div key={term}><dt>{term}</dt><dd>{text}</dd></div>)}</dl></main>}

export function ActivityPage(){return <ActivityMonitor embedded/>}
