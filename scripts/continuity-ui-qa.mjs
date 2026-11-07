// Disposable full-dashboard QA. No model calls or production episode writes.
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium, expect } from "@playwright/test";
import { ensureBrowser } from "@remotion/renderer";
expect.configure({timeout:30000});

const root=process.cwd(), store=path.join(root,"artifacts",`continuity-browser-${Date.now()}`);
await mkdir(store,{recursive:true});
const env={...process.env,ODD_DATA_ROOT:store,ODD_AI_PROVIDER:"manual",ODD_PORT:"8137",PYTHONUTF8:"1"};
const python=path.join(root,".venv/Scripts/python.exe");
const code=`
import json
from services.api import core,creative
from tests.fixtures import IDEA,SCRIPT,NARRATION,package
from PIL import Image
core.init_db()
ep=creative.create_episode(IDEA)
core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
run=creative.approve(ep['id'],NARRATION)
p=package()
p['visual_continuity']['bible']['assets'][0]['reference_ids']=['REF_MIRA']
p['visual_continuity']['bible']['references']=[dict(id='REF_MIRA',category='character',path=None,sha256=None,approved=False,essential=False)]
creative.complete_run(run['run_id'],p,manual=True)
root=creative.epdir(core.episode(ep['id']))
Image.new('RGB',(90,160),'gray').save(root/'05_assets/images/S001.png')
print(json.dumps(dict(id=ep['id'],token=core.controller_token())))
`;
const fixture=await new Promise((resolve,reject)=>{
  const child=spawn(python,["-c",code],{cwd:root,env,windowsHide:true});let out="",err="";
  child.stdout.on("data",b=>out+=b);child.stderr.on("data",b=>err+=b);
  child.on("exit",c=>c?reject(Error(err)):resolve(JSON.parse(out)));
});
const server=spawn(python,["-m","uvicorn","services.api.main:app","--host","127.0.0.1","--port","8137"],{cwd:root,env,windowsHide:true,stdio:"ignore"});
let browser;
try {
  for(let i=0;i<100;i++) {
    try { const r=await fetch("http://127.0.0.1:8137/api/episodes");if(r.ok)break; } catch {}
    await new Promise(r=>setTimeout(r,200));
  }
  browser=await chromium.launch({executablePath:(await ensureBrowser()).path,headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on("pageerror",error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:8137/flow?episode=${fixture.id}#controller=${fixture.token}`);
  await expect(page.getByText("Visual continuity",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Visual Bible and references"}).click();
  await expect(page.getByText("Mira",{exact:true}).first()).toBeVisible();
  await page.getByLabel("Reference image for REF_MIRA").selectOption("05_assets/images/S001.png");
  await page.getByRole("button",{name:"Pin approved reference",exact:true}).click();
  await expect(page.getByText("Approved reference pinned. No attachment was sent to Flow.",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Batch review in storyboard order"}).click();
  await expect(page.getByAltText("Generated image for S001; requires visual review")).toBeVisible();
  await page.getByRole("button",{name:"Reviewed: reject",exact:true}).click();
  await expect(page.getByText(/Latest owner record: REJECT/)).toBeVisible();
  await page.getByRole("button",{name:"Prepare scene regeneration",exact:true}).first().click();
  await expect(page.getByRole("link",{name:"Download scene regeneration JSON"})).toBeVisible();
  await page.screenshot({path:path.join(store,"desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(store,"mobile.png"),fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
  expect(overflow).toBe(false);expect(errors).toEqual([]);
  await writeFile(path.join(store,"results.json"),JSON.stringify({status:"PASS",checks:["bible","ordered batch thumbnails","owner reject persistence","pinned scene regeneration download","mobile overflow"],pageErrors:errors},null,2));
  console.log(JSON.stringify({status:"PASS",output:store}));
} finally {await browser?.close();server.kill();}
