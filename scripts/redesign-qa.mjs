import {chromium,expect} from '@playwright/test';
import {ensureBrowser} from '@remotion/renderer';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const base='http://127.0.0.1:5174';
const store=new URL('../artifacts/preview-data/',import.meta.url);
const token=JSON.parse(await readFile(new URL('data/controller-access.json',store),'utf8')).token;
const browser=await chromium.launch({executablePath:(await ensureBrowser()).path});
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
await mkdir('artifacts/new-ui',{recursive:true});
const routes={'Home':'/','Master Prompt':'/master-prompt','Ideas':'/ideas','Script Studio':'/script','Episode Workspace':'/workspace','Google Flow Prompts':'/flow','Asset Manager':'/assets','Edit Studio':'/studio','Exports':'/exports','Analytics':'/analytics','Settings':'/settings','Production Queue':'/queue','AI Activity':'/activity','System Health':'/health','How to Use':'/help'};
const checks=[];
try{
 await page.goto(base+'/#controller='+token);await expect(page.getByRole('heading',{level:1})).toBeVisible();
 for(const [name,path] of Object.entries(routes)){
  await page.getByRole('link',{name,exact:true}).click();await expect(page).toHaveURL(base+path);await expect(page.getByRole('heading',{level:1})).toBeVisible();
  await page.screenshot({path:`artifacts/new-ui/${name.replaceAll(' ','-')}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),name+' desktop overflow').toBe(false);
  checks.push(name+' route and desktop layout');
 }
 await page.reload();await expect(page.getByRole('heading',{level:1,name:'How to Use'})).toBeVisible();
 await page.getByLabel('Search help').fill('approval');await expect(page.getByRole('button',{name:/Approve a script/})).toBeVisible();
 await page.goBack();await expect(page).toHaveURL(base+'/health');await page.goForward();await expect(page).toHaveURL(base+'/help');checks.push('Refresh and browser back/forward');
 await page.getByRole('button',{name:'Toggle Sidebar'}).click();await page.reload();expect(await page.evaluate(()=>localStorage.getItem('odd-sidebar'))).toBe('collapsed');
 await page.getByRole('link',{name:'Ideas',exact:true}).hover();await expect(page.getByRole('tooltip',{name:'Ideas',exact:true})).toBeVisible();await page.getByRole('button',{name:'Toggle Sidebar'}).click();checks.push('Sidebar preference and collapsed tooltip');
 await page.setViewportSize({width:390,height:844});
 for(const [name,path] of Object.entries(routes)){
  await page.goto(base+path);await expect(page.getByRole('heading',{level:1})).toBeVisible();await page.screenshot({path:`artifacts/new-ui/${name.replaceAll(' ','-')}-mobile.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),name+' mobile overflow').toBe(false);
 }
 await page.getByRole('button',{name:'Toggle Sidebar'}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('link',{name:'Ideas',exact:true}).click();await expect(page.getByRole('dialog')).not.toBeVisible();await expect(page).toHaveURL(base+'/ideas');checks.push('Mobile Sheet navigation and every route layout');
 await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:/AI Activity,/}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();checks.push('Activity Sheet Escape');
 expect(errors).toEqual([]);
 await writeFile('artifacts/new-ui/result.json',JSON.stringify({passed:true,checks,errors},null,2));console.log(JSON.stringify({passed:true,checks,errors},null,2));
}catch(e){await page.screenshot({path:'artifacts/new-ui/failure.png',fullPage:true});throw e}finally{await browser.close()}
