// Manual-provider browser integration only. Never launches an AI model.
import {chromium,expect} from '@playwright/test';
import {ensureBrowser} from '@remotion/renderer';
import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {createServer} from 'node:net';

const root=process.cwd();
const port=await new Promise((resolve,reject)=>{const probe=createServer();probe.on('error',reject);probe.listen(0,'127.0.0.1',()=>{const value=probe.address().port;probe.close(()=>resolve(value))})});
const url=`http://127.0.0.1:${port}`;
const store=path.join(root,'artifacts/genre-ui',new Date().toISOString().replaceAll(/[:.]/g,'-'));
await mkdir(store,{recursive:true});
const server=spawn(path.join(root,'.venv/Scripts/python.exe'),['-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port',String(port)],{
  cwd:root,env:{...process.env,ODD_DATA_ROOT:store,ODD_PORT:String(port),ODD_AI_PROVIDER:'manual'},windowsHide:true,stdio:['ignore','pipe','pipe']});
let logs='',browser;
server.stdout.on('data',d=>logs+=d);server.stderr.on('data',d=>logs+=d);
async function fixture(payload){
  return new Promise((resolve,reject)=>{
    const p=spawn(path.join(root,'.venv/Scripts/python.exe'),['-c','import json,sys; from tests.genre_fixtures import concept_batch; print(json.dumps(concept_batch(json.load(sys.stdin))))'],{cwd:root,windowsHide:true});
    let out='';p.stdout.on('data',d=>out+=d);p.on('error',reject);p.on('exit',code=>code?reject(Error('Fixture failed')):resolve(JSON.parse(out)));p.stdin.end(JSON.stringify(payload));
  });
}
try{
  let ready=false;
  for(let i=0;i<100;i++){try{if((await fetch(url+'/api/status')).ok){ready=true;break}}catch{}await new Promise(r=>setTimeout(r,200))}
  if(!ready)throw Error('Disposable station did not start');
  const {token}=JSON.parse(await readFile(path.join(store,'data/controller-access.json'),'utf8'));
  const request=async(route,method='GET',body)=>{
    const r=await fetch(url+'/api'+route,{method,headers:{'content-type':'application/json','x-odd-controller':token},body:body===undefined?undefined:JSON.stringify(body)});
    const value=await r.json();if(!r.ok)throw Error(JSON.stringify(value));return value;
  };
  browser=await chromium.launch({headless:true,executablePath:(await ensureBrowser()).path});
  const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url+'/#controller='+token);
  await page.getByRole('button',{name:'Create New Reel',exact:true}).click();
  await expect(page.getByRole('heading',{name:'What Kind of Story Are We Creating?',exact:true})).toBeVisible();
  await expect(page.locator('.category-card')).toHaveCount(8);
  expect((await request('/runs')).length).toBe(0);
  const taxonomy=await request('/genres');
  for(const group of taxonomy.groups){
    await page.getByRole('button',{name:new RegExp(group.name.replaceAll(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).click();
    await expect(page.locator('.genre-options .genre-option')).toHaveCount(group.genres.length+1);
  }
  await page.getByRole('button',{name:/COMEDY & DARK COMEDY/}).click();
  await page.getByRole('button',{name:'Comedy',exact:true}).click();
  await page.screenshot({path:path.join(store,'01-genres-desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Generate 5 Story Ideas',exact:true}).click();
  const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button',{name:'Cancel',exact:true})).toBeFocused();
  await page.keyboard.press('Shift+Tab');await expect(dialog.getByRole('button',{name:'Confirm & Generate',exact:true})).toBeFocused();
  await page.keyboard.press('Tab');await expect(dialog.getByRole('button',{name:'Cancel',exact:true})).toBeFocused();
  expect((await request('/runs')).length).toBe(0);
  await page.screenshot({path:path.join(store,'02-confirmation.png')});
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Generate 5 Story Ideas',exact:true})).toBeFocused();
  await page.getByRole('button',{name:'Generate 5 Story Ideas',exact:true}).click();
  await page.getByRole('button',{name:'Confirm & Generate',exact:true}).click();
  await expect(page.getByText('Manual handoff ready',{exact:true})).toBeVisible();
  const state=JSON.parse(await page.evaluate(()=>localStorage.getItem('odd-frame-genre-selection-v2')));
  const first=await request('/idea-sessions/'+state.session),batch=first.batches[0];
  const bundle=await request('/runs/'+batch.run_id+'/request'),payload=JSON.parse(bundle.request.messages[1].content);
  expect(payload.primary_genre_id).toBe('comedy');expect(payload.idea_count).toBe(5);
  expect(bundle.provenance.skills.length).toBe(4);expect(bundle.request.messages[0].content.length).toBeGreaterThan(110000);
  const concepts=await fixture(payload),invalid=structuredClone(concepts);invalid.ideas.pop();
  await page.getByLabel('Structured idea response').fill(JSON.stringify(invalid));
  await page.getByRole('button',{name:'Validate & Import Five Ideas',exact:true}).click();
  await expect(page.getByRole('alert').filter({hasText:/5 items/})).toBeVisible();
  await expect(page.locator('.concept-card')).toHaveCount(0);
  await page.reload();await page.getByRole('button',{name:'Ideas',exact:true}).click();
  await expect(page.getByRole('alert').filter({hasText:'Last import failed validation:'})).toBeVisible();
  await page.getByLabel('Structured idea response').fill(JSON.stringify(concepts));
  await page.getByRole('button',{name:'Validate & Import Five Ideas',exact:true}).click();
  await expect(page.locator('.concept-card')).toHaveCount(5,{timeout:15000});
  await page.locator('.concept-card').first().getByText('View Full Concept',{exact:false}).click();
  await expect(page.locator('.concept-card').first().getByText(/Suggested duration:/)).toBeVisible();
  await page.screenshot({path:path.join(store,'03-concepts-desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Generate Another 5 Ideas',exact:true}).click();
  await expect(dialog).toContainText('Comedy');await page.getByRole('button',{name:'Confirm & Generate',exact:true}).click();
  await expect(page.getByRole('button',{name:'Cancel manual request',exact:true})).toBeVisible();
  const second=await request('/idea-sessions/'+state.session),next=second.batches[1];
  const nextPayload=JSON.parse((await request('/runs/'+next.run_id+'/request')).request.messages[1].content);
  expect(nextPayload.prior_concepts.length).toBe(5);expect(nextPayload.primary_genre_id).toBe('comedy');
  await page.getByRole('button',{name:'Cancel manual request',exact:true}).click();
  await expect(page.getByLabel('Generation batch')).toContainText('CANCELLED',{timeout:10000});
  await page.getByLabel('Generation batch').selectOption(batch.id);
  await expect(page.locator('.concept-card')).toHaveCount(5);
  await page.reload();
  await page.getByRole('button',{name:'Ideas',exact:true}).click();
  await expect(page.locator('.concept-card')).toHaveCount(5);
  await expect(page.getByLabel('Generation batch')).toHaveValue(batch.id);
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(store,'04-concepts-mobile.png'),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.getByRole('button',{name:'Change Genre',exact:true}).click();
  await page.screenshot({path:path.join(store,'05-genres-mobile.png'),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.getByRole('button',{name:/ROMANCE & OTHER/}).click();
  await page.getByRole('button',{name:'Romance',exact:true}).click();
  await page.getByRole('button',{name:'I have my own story',exact:true}).click();
  const title='The Haunted Hotel',premise='A terrifying monster guards a haunted hotel. There is no love.';
  await page.getByLabel('Working title').fill(title);await page.getByLabel('Your story premise').fill(premise);
  await page.getByRole('button',{name:'Develop This Story',exact:true}).click();
  await expect(dialog).toContainText('horror elements');
  await expect(page.getByRole('button',{name:'Confirm & Develop',exact:true})).toBeDisabled();
  await page.getByLabel('Keep My Premise exactly as supplied').check();
  await page.getByRole('button',{name:'Cancel',exact:true}).click();
  expect((await request('/episodes')).length).toBe(0);
  await page.setViewportSize({width:1600,height:1100});
  await page.getByLabel('Saved story sessions').selectOption(state.session);
  await page.getByLabel('Generation batch').selectOption(batch.id);
  await expect(page.locator('.concept-card')).toHaveCount(5);
  await page.getByRole('button',{name:'Select This Story',exact:true}).first().click();
  await expect(page.getByRole('heading',{name:'The story, in your words',exact:true})).toBeVisible({timeout:30000});
  const episodes=await request('/episodes'),episode=await request('/episodes/'+episodes[0].id);
  expect(episode.data.genre_selection.primary_genre_id).toBe('comedy');
  expect(episode.data.genre_selection.idea_batch_id).toBe(batch.id);
  expect(episode.data.story_concept.title).toBe(concepts.ideas[0].title);
  const script=JSON.parse((await request('/runs/'+episode.data.pending_run+'/request')).request.messages[1].content);
  expect(script.genre_context.primary_genre_id).toBe('comedy');
  const jobs=await request('/activity'),job=jobs.find(j=>j.job_id===batch.run_id);
  expect(job.events.some(e=>e.type==='category.confirmed')).toBe(true);
  expect(job.events.some(e=>e.type==='file.saved'&&e.completed===5&&e.total===5)).toBe(true);
  expect(job.events.at(-1).message).toContain('Select one of the five');
  expect(errors).toEqual([]);
  const report={result:'PASS',mode:'Manual integration with synthetic concepts; no live model usage',store,executed:['8 groups / 24 genres','No generation before confirmation','Dialog focus / Escape restoration','Full pinned request and actual selected genre','Invalid four-concept import rejected','Five validated concept cards and expandable details','Another five retains genre and supplies prior history','Manual request cancellation','Batch switching and refresh restoration','390px layout without horizontal overflow','Custom premise warning and explicit choice','Concept-to-script episode identity and provenance','Real normalized activity milestones','No browser runtime errors']};
  await writeFile(path.join(store,'RESULT.json'),JSON.stringify(report,null,2));await writeFile(path.join(root,'artifacts/genre-ui/latest.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}catch(error){await writeFile(path.join(store,'server.log'),logs);throw error}finally{if(browser)await browser.close();server.kill()}
