"""Real end-to-end disposable pipeline render. Never edits production episodes."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
RUN=ROOT/'artifacts'/'render-smoke'/time.strftime('%Y%m%d-%H%M%S')
RUN.mkdir(parents=True,exist_ok=False)
os.environ['ODD_DATA_ROOT']=str(RUN)
os.environ['ODD_PORT']='8124'
os.environ['ODD_AI_PROVIDER']='manual'
from services.api.core import init_db,read_json,write_json,episode,epdir
from services.api.media import command,probe
from tests.fixtures import IDEA,SCRIPT,NARRATION,package
from PIL import Image,ImageDraw
import httpx

def stamp(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def main():
    print('Disposable isolated store: '+str(RUN),flush=True)
    fixtures=RUN/'fixtures';fixtures.mkdir()
    phrases=['The key was gone.','The door was open.','She stayed outside.']
    # Built-in Windows TTS is ONLY a clearly labeled engineering fixture, not ElevenLabs output.
    speech_script=fixtures/'speech.ps1'
    speech_script.write_text("Add-Type -AssemblyName System.Speech\n$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer\n$voice.Rate = 1\n"+'\n'.join(f"$voice.SetOutputToWaveFile('{str(fixtures/f'voice{i}.wav').replace(chr(39),chr(39)*2)}')\n$voice.Speak('{p}')\n$voice.SetOutputToNull()" for i,p in enumerate(phrases))+"\n$voice.Dispose()\n",encoding='utf-8')
    command(['powershell.exe','-NoProfile','-File',speech_script])
    durations=[float(probe(fixtures/f'voice{i}.wav')['format']['duration']) for i in range(3)]
    concat=fixtures/'voices.txt';concat.write_text('\n'.join("file '"+str(fixtures/f'voice{i}.wav').replace('\\','/')+"'" for i in range(3)),encoding='utf-8')
    narration=fixtures/'narration.wav'
    command(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',concat,'-c:a','pcm_s16le',narration])
    total=sum(durations)
    cues=[];start=0
    for i,(phrase,duration) in enumerate(zip(phrases,durations)):
        cues.append(f'{i+1}\n{stamp(start)} --> {stamp(start+duration)}\n{phrase}\n');start+=duration
    (fixtures/'captions.srt').write_text('\n'.join(cues),encoding='utf-8')
    music=fixtures/'instrumental.wav'
    command(['ffmpeg','-y','-v','error','-f','lavfi','-i',f'sine=frequency=220:duration={total}', '-f','lavfi','-i',f'sine=frequency=330:duration={total}', '-filter_complex','[0:a][1:a]amix=inputs=2,volume=0.3','-ar','48000',music])
    for i in range(3):
        image=Image.new('RGB',(1080,1920),'#14171C');draw=ImageDraw.Draw(image)
        draw.rectangle((0,1100,1080,1920),fill='#41464E')
        draw.rectangle((675,550,985,1500),fill='#7D838B',outline='#090b10',width=15)
        draw.rectangle((700,575,960,1480),fill='#14171C' if i>0 else '#41464E')
        draw.rectangle((610,920,655,1020),fill='#FFD43B',outline='#090b10',width=8)
        draw.ellipse((220,1230,450,1480),fill='#41464E',outline='#090b10',width=15)
        draw.ellipse((225,1070,405,1260),fill='#F1EBDD',outline='#090b10',width=12)
        draw.ellipse((230,930,285,1120),fill='#F1EBDD',outline='#090b10',width=10)
        draw.ellipse((335,930,390,1120),fill='#F1EBDD',outline='#090b10',width=10)
        draw.ellipse((335,1140,352,1157),fill='#14171C')
        draw.line((350,1200,375,1190+i*3),fill='#14171C',width=6)
        image.save(fixtures/f'S{i+1:03d}.png')
    log=(RUN/'server.log').open('w',encoding='utf-8')
    server=subprocess.Popen([sys.executable,'-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8124'],cwd=ROOT,env=os.environ.copy(),stdout=log,stderr=log)
    try:
        with httpx.Client(base_url='http://127.0.0.1:8124',timeout=300) as client:
            for attempt in range(60):
                try:
                    if client.get('/api/status').status_code==200:break
                except httpx.HTTPError:time.sleep(.5)
            else:raise RuntimeError('Smoke API did not start')
            client.headers['X-Odd-Controller']=json.loads((RUN/'data/controller-access.json').read_text(encoding='utf-8'))['token']
            def post(path,payload=None,**kwargs):
                response=client.post(path,json=payload,**kwargs) if 'files' not in kwargs else client.post(path,**kwargs)
                response.raise_for_status();return response.json()
            ep=post('/api/episodes',IDEA);eid=ep['id'];prefix=f'/api/episodes/{eid}'
            post(prefix+'/draft',SCRIPT)
            run=post(prefix+'/approve',{'narration':NARRATION})
            post('/api/runs/'+run['run_id']+'/import',package())
            handles=[(fixtures/f'S{i:03d}.png').open('rb') for i in range(1,4)]
            try:post(prefix+'/assets/images',files=[('files',(f'S{i+1:03d}.png',h,'image/png')) for i,h in enumerate(handles)])
            finally:
                for h in handles:h.close()
            for kind,name in [('narration','narration.wav'),('subtitles','captions.srt'),('music','instrumental.wav')]:
                with (fixtures/name).open('rb') as handle:post(prefix+'/assets/'+kind,files=[('files',(name,handle))])
            post(prefix+'/music-rights',{'instrumental_confirmed':True,'evidence':'Synthetic two-tone QA instrumental generated by this smoke test. Not a production music recommendation.'})
            report=post(prefix+'/assets/refresh');assert report['valid'],report
            print(f'Created {ep["code"]}; all imports passed. Actual TTS duration: {total:.3f}s',flush=True)
            deadline=time.monotonic()+900;last='';render_requested=False
            while time.monotonic()<deadline:
                detail=client.get(prefix).json()
                state=detail['status'];job=detail['jobs'][0] if detail['jobs'] else {}
                message=f'{state} · {job.get("stage")}'
                if message!=last:print(message,flush=True);last=message
                if state=='FAILED':raise RuntimeError(detail['data'].get('error'))
                if state=='EDIT_READY' and not render_requested:
                    saved=client.get(prefix+'/editor').json()
                    post(prefix+'/editor/render',{'revision':saved['state']['revision']});render_requested=True
                if state=='COMPLETE':break
                time.sleep(2)
            else:raise TimeoutError('Render did not finish in 15 minutes')
            final=detail['data']['exports'][-1]
            qc=read_json(RUN/detail['path']/'07_export/QC_REPORT.json')
            mix=read_json(RUN/detail['path']/'06_edit/audio_mix.json')
            assert qc['valid'] and qc['decoded']
            assert qc['video']['width']==1080 and qc['video']['height']==1920 and qc['video']['r_frame_rate']=='30/1'
            assert qc['audio']['codec_name']=='aac' and qc['video']['codec_name']=='h264'
            assert mix['sources']==['narration','instrumental'] and not mix['sfx']
            assert mix['measured_integrated_gap_db']>=18
            assert abs(float(qc['loudness']['input_i'])+16)<1.5
            # Inspect decoded frames: image region stays static within a shot; text changes during entrance.
            from PIL import ImageChops,ImageStat
            finalpath=RUN/final['path']
            for tag,at in [('entrance',0),('hold_a',.3),('hold_b',.8)]:
                command(['ffmpeg','-y','-v','error','-ss',str(at),'-i',finalpath,'-frames:v','1',RUN/f'{tag}.png'])
            with Image.open(RUN/'hold_a.png') as a,Image.open(RUN/'hold_b.png') as b,Image.open(RUN/'entrance.png') as entrance:
                static_diff=sum(ImageStat.Stat(ImageChops.difference(a.crop((0,1050,1080,1920)),b.crop((0,1050,1080,1920)))).mean)/3
                text_diff=sum(ImageStat.Stat(ImageChops.difference(a.crop((95,500,985,800)),entrance.crop((95,500,985,800)))).mean)/3
            assert static_diff<1.5,('Unexpected image-region motion',static_diff)
            assert text_diff>.5,('Caption entrance did not change frames',text_diff)
            summary=dict(result='PASS',synthetic_qa_only=True,store=str(RUN),export=str(RUN/final['path']),duration_seconds=total,
                         video=dict(width=1080,height=1920,fps=30,codec='h264'),audio=dict(codec='aac',lufs=qc['loudness']['input_i'],true_peak=qc['loudness']['input_tp'],gap_db=mix['measured_integrated_gap_db']),
                         frame_checks=dict(static_region_mean_difference=static_diff,caption_entrance_mean_difference=text_diff),
                         executed=['HTTP story selection','owner draft import','single script approval','full four-skill loading','manual Package import','all preproduction documents','bulk image upload','audio/SRT/music imports','automatic editable draft','measured audio ducking','explicit render from saved revision','Remotion preview and final','FFprobe and complete decode','black-frame check','static image region comparison','animated caption entrance frame comparison'],
                         limitations=['Synthetic QA speech and illustrations, not genuine ElevenLabs/Google Flow production assets','No live paid model call','No acoustic forced alignment or subjective creative quality proof'])
            write_json(RUN/'RESULT.json',summary)
            write_json(ROOT/'artifacts/render-smoke/latest.json',summary)
            print(json.dumps(summary,indent=2),flush=True)
    finally:
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill()
        log.close()

if __name__=='__main__':main()
