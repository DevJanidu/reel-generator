import {chromium,expect} from '@playwright/test';
import {ensureBrowser} from '@remotion/renderer';
import {mkdir,writeFile} from 'node:fs/promises';
const browser=await chromium.launch({executablePath:(await ensureBrowser()).path});
const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));const evidence=[];
await mkdir('artifacts/ideas-layout',{recursive:true});
try{
 for(const width of [1920,1440,768,390]){
  await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:5174/ideas');await expect(page.locator('.category-card')).toHaveCount(8);
  const cards=await page.locator('.category-card').evaluateAll(nodes=>nodes.map(el=>{const rect=el.getBoundingClientRect();return {radius:parseFloat(getComputedStyle(el).borderRadius),padding:parseFloat(getComputedStyle(el).paddingLeft),variant:el.getAttribute('data-variant'),contained:[...el.children].every(child=>{const r=child.getBoundingClientRect();return r.left>=rect.left+18&&r.right<=rect.right-18&&r.top>=rect.top+18&&r.bottom<=rect.bottom-18})}}));
  expect(cards.every(c=>c.radius===18&&c.padding>=20&&c.variant==='outline'&&c.contained),JSON.stringify({width,cards})).toBe(true);
  await page.getByRole('button',{name:/BETRAYAL & REVENGE/}).click();await expect(page.getByRole('button',{name:/BETRAYAL & REVENGE/})).toHaveAttribute('aria-pressed','true');await page.getByRole('button',{name:'Betrayal',exact:true}).click();await expect(page.getByRole('button',{name:'Betrayal',exact:true})).toHaveAttribute('aria-pressed','true');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`artifacts/ideas-layout/ideas-${width}.png`,fullPage:true});evidence.push({width,cards:cards.length,contained:true,radius:18});
 }
 expect(errors).toEqual([]);await writeFile('artifacts/ideas-layout/result.json',JSON.stringify({passed:true,evidence,errors},null,2));console.log(JSON.stringify({passed:true,evidence,errors},null,2));
}finally{await browser.close()}
