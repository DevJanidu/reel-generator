import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {api,ApiError} from './api';
describe('controller API transport',()=>{
 beforeEach(()=>{vi.stubGlobal('sessionStorage',{getItem:()=> 'test-session-capability'});vi.stubGlobal('localStorage',{getItem:()=>null})});
 afterEach(()=>vi.unstubAllGlobals());
 it('passes cancellation through to fetch and preserves the authorization header',async()=>{
  const fetcher=vi.fn().mockResolvedValue(new Response('{"ok":true}'));vi.stubGlobal('fetch',fetcher);const controller=new AbortController();
  expect(await api('/settings','PUT',{provider:'manual'},controller.signal)).toEqual({ok:true});
  expect(fetcher).toHaveBeenCalledWith('/api/settings',expect.objectContaining({signal:controller.signal,body:'{"provider":"manual"}',headers:expect.objectContaining({'X-Odd-Controller':'test-session-capability'})}));
 });
 it('does not set a multipart boundary manually',async()=>{const fetcher=vi.fn().mockResolvedValue(new Response('{}'));vi.stubGlobal('fetch',fetcher);const body=new FormData();body.append('file',new Blob(['fixture']),'test.txt');await api('/episodes/1/assets/images','POST',body);expect(fetcher.mock.calls[0][1].body).toBe(body);expect(fetcher.mock.calls[0][1].headers).not.toHaveProperty('Content-Type')});
 it('preserves actionable backend validation errors',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('{"detail":"Approved narration is immutable"}',{status:422})));await expect(api('/episodes/1/draft','POST',{})).rejects.toMatchObject({message:'Approved narration is immutable',status:422})});
 it('reports unreadable server responses without exposing HTML',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html>private traceback</html>',{status:500})));await expect(api('/status')).rejects.toMatchObject({message:'Request failed. Please retry.',status:500})});
 it('allows an empty successful response',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(null,{status:204})));expect(await api('/runs/one/cancel','POST')).toBeNull()});
 it('keeps aborted requests aborted instead of inventing a server error',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new DOMException('Aborted','AbortError')));await expect(api('/status')).rejects.toMatchObject({name:'AbortError'})});
});
