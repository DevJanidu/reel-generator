// Real browser test against a disposable, native-prepared copy of the genuine episode.
import {chromium,expect} from '@playwright/test';
import {ensureBrowser} from '@remotion/renderer';
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
const root=process.cwd();
const report=JSON.parse(await readFile('artifacts/studio-upgrade/latest-draft.json','utf8').catch(()=>readFile('artifacts/studio-upgrade/latest.json','utf8')));
const store=process.argv.slice(2).find(a=>!a.startsWith('--'))||report.store,origin='http://127.0.0.1:8131',out=path.join(store,'browser');await mkdir(out,{recursive:true});
const server=spawn(path.join(root,'.venv/Scripts/python.exe'),['-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8131'],{
  cwd:root,env:{...process.env,ODD_DATA_ROOT:store,ODD_PORT:'8131',ODD_AI_PROVIDER:'manual'},windowsHide:true,stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',d=>logs+=d);server.stderr.on('data',d=>logs+=d);let browser;
try{
  for(let i=0;i<100;i++){try{if((await fetch(origin+'/api/episodes')).ok)break}catch{}await new Promise(r=>setTimeout(r,200))}
  const browserInfo=await ensureBrowser();browser=await chromium.launch({headless:true,executablePath:browserInfo.path,args:['--autoplay-policy=no-user-gesture-required']});
  const page=await browser.newPage({viewport:{width:1600,height:1150}}),errors=[],mutations=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()!=='GET')mutations.push(r.url())});
  const access=JSON.parse(await readFile(path.join(store,'data/controller-access.json'),'utf8')).token;
  await page.goto(origin+'/#controller='+access);
  await expect(page.getByRole('heading',{name:'Your next story starts here.'})).toBeVisible();
  const started=performance.now();await page.goto(origin+'/episodes/1/editor');
  await expect(page.getByRole('button',{name:'Render Final Video',exact:true})).toBeVisible({timeout:30000});
  await expect(page.locator('[data-caption]')).toHaveCount(1);
  await page.screenshot({path:path.join(out,'editor-loaded.png'),fullPage:true});
  const loadedMs=performance.now()-started;
  await expect(page.locator('.images-track .timeline-clip')).toHaveCount(18);
  await expect(page.locator('.captions-track .timeline-clip')).toHaveCount(82);
  await expect(page.locator('.timeline-panel .waveform')).toHaveCount(2);
  // Make reruns exercise a real saved delta rather than arriving at an already saved gain.
  await page.getByLabel('Music gain',{exact:true}).press('End');
  await page.waitForTimeout(1600);
  await page.getByRole('button',{name:'Play / Pause',exact:true}).click();
  await page.waitForTimeout(3200);await page.getByRole('button',{name:'Play / Pause',exact:true}).click();
  const playhead=await page.getByLabel('Timeline playhead').inputValue();expect(Number(playhead)).toBeGreaterThan(50);
  // Explicitly select a narration-grounded phrase, then check DOM and controls.
  await page.locator('.captions-track .timeline-clip').nth(2).click();
  await expect(page.getByLabel('Caption words')).toBeVisible();
  await page.getByLabel('Caption animation').selectOption('glow_pop');
  await expect(page.locator('[data-caption][data-preset="glow_pop"]')).toHaveCount(1);
  const glow=page.getByLabel('Glow strength',{exact:true});await glow.press('Home');await glow.press('ArrowRight');
  const music=page.getByLabel('Music gain',{exact:true});await music.press('Home');for(let i=0;i<35;i++)await music.press('ArrowRight');
  await expect(music).toHaveValue('0.35');
  const volumes=await page.locator('audio').evaluateAll(nodes=>nodes.map(n=>({volume:n.volume,muted:n.muted,src:n.currentSrc.split('/').at(-1)})));
  expect(volumes.some(n=>Math.abs(n.volume-.35)<.02)).toBeTruthy();
  await page.waitForTimeout(2000);
  await expect(page.getByText(/Saved revision \d+/)).toBeVisible();
  await page.locator('.images-track .timeline-clip').nth(1).click();
  await page.getByLabel('Scene transition',{exact:true}).selectOption('crossfade');
  await page.waitForTimeout(1800);
  await page.getByRole('button',{name:'Undo',exact:true}).click();await page.getByRole('button',{name:'Redo',exact:true}).click();
  await page.waitForTimeout(1800);await page.screenshot({path:path.join(out,'editor-desktop.png'),fullPage:true});
  await page.reload();await expect(page.getByLabel('Music gain',{exact:true})).toHaveValue('0.35');
  await page.locator('.captions-track .timeline-clip').nth(2).click();await expect(page.getByLabel('Caption animation')).toHaveValue('glow_pop');
  await page.locator('.images-track .timeline-clip').nth(1).click();await expect(page.getByLabel('Scene transition')).toHaveValue('crossfade');
  if(process.argv.includes('--providers')){
    await page.evaluate(()=>{window.__observedActivity=[];window.__providerStream=new EventSource('/api/activity/stream');window.__providerStream.addEventListener('activity',e=>window.__observedActivity.push(JSON.parse(e.data)))});
    const live=fetch(origin+'/api/providers/codex_cli/test',{method:'POST',headers:{'X-Odd-Controller':access}}).then(r=>r.json());
    await page.getByRole('button',{name:/AI Activity|running job/}).click();
    await expect(page.getByText('codex_cli · Testing provider connection',{exact:false})).toBeVisible({timeout:30000});
    await page.screenshot({path:path.join(out,'activity-running-real-codex.png'),fullPage:true});
    const diagnostic=await live;expect(diagnostic.success).toBeTruthy();
    await page.waitForTimeout(1800);
    const observed=await page.evaluate(()=>{window.__providerStream.close();return window.__observedActivity});
    expect(observed.some(e=>e.provider==='codex_cli'&&e.message==='Provider session established')).toBeTruthy();
    await page.getByRole('button',{name:'Close',exact:true}).click();
  }
  const jobs=await (await fetch(origin+'/api/activity')).json();
  const codex=jobs.find(j=>j.provider==='codex_cli');expect(codex.events.some(e=>e.type==='ai.activity'&&e.message==='Provider session established')).toBeTruthy();
  await page.getByRole('button',{name:/AI Activity|running job/}).click();
  await expect(page.getByRole('complementary',{name:'AI Activity Monitor'})).toBeVisible();
  await expect(page.getByText('codex_cli · Connection verified',{exact:false})).toBeVisible();
  await page.screenshot({path:path.join(out,'activity-desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Close',exact:true}).click();
  const replay=await page.evaluate(async()=>{
    return await new Promise(resolve=>{const events=[],source=new EventSource('/api/activity/stream');const timer=setTimeout(()=>{source.close();resolve(events)},1800);source.addEventListener('activity',e=>{events.push({event:JSON.parse(e.data),cursor:e.lastEventId})})});
  });
  expect(replay.length).toBeGreaterThan(5);expect(new Set(replay.map(e=>e.event.event_id)).size).toBe(replay.length);
  const resume=await page.evaluate(async cursor=>await new Promise(resolve=>{const events=[],source=new EventSource('/api/activity/stream?cursor='+encodeURIComponent(cursor));setTimeout(()=>{source.close();resolve(events)},1200);source.addEventListener('activity',e=>events.push(JSON.parse(e.data).event_id))}),replay.at(-1).cursor);
  expect(resume.length).toBe(0);
  expect(mutations.every(p=>p.endsWith('/editor'))).toBeTruthy();
  expect(errors).toEqual([]);
  let rebuildRetried=false;
  await page.route('**/api/episodes/1/editor',route=>route.fulfill({status:422,contentType:'application/json',body:JSON.stringify({detail:'An explicit draft rebuild has not completed. Retry the rebuild.'})}));
  await page.route('**/api/episodes/1/editor/rebuild',route=>{rebuildRetried=true;return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({job_id:123})})});
  await page.reload();
  await page.getByRole('button',{name:'Retry draft rebuild',exact:true}).click();
  await expect.poll(()=>rebuildRetried).toBeTruthy();
  await page.unroute('**/api/episodes/1/editor');await page.unroute('**/api/episodes/1/editor/rebuild');
  await page.goto(origin+'/help');await expect(page.getByRole('heading',{name:'Understanding AI Job Progress'})).toBeVisible();
  await page.setViewportSize({width:750,height:1100});await page.goto(origin+'/episodes/1/editor');await page.screenshot({path:path.join(out,'editor-narrow.png'),fullPage:true});
  const result={passed:true,editor_load_ms:Math.round(loadedMs),playback_frames_after_3_2_seconds:Number(playhead),live_audio_volumes:volumes,
    scenes:18,captions:82,save_restore:true,caption_preset_live:true,transition_save_restore:true,undo_redo:true,
    render_requests_during_adjustments:mutations.filter(p=>p.endsWith('/render')).length,actual_codex_events_visible:true,sse_replayed:replay.length,sse_resume_duplicates:resume.length,failed_rebuild_retry_ui:true,browser_errors:errors};
  await writeFile(path.join(out,'RESULT.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{await browser?.close();server.kill();await writeFile(path.join(out,'controller.log'),logs)}
