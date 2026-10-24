import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { readFile, mkdir } from 'node:fs/promises';
import { resolve, relative, isAbsolute, extname } from 'node:path';

let browserRun=0;
// Local dist + isolated browser. No provider download or commercial runtime.
export async function openLocalBrowser(outputDirectory='dist') {
  const root = resolve(outputDirectory);
  const server = createServer(async (request, response) => {
    try {
      const path = decodeURIComponent(new URL(request.url ?? '/', 'http://localhost').pathname);
      if (path === '/favicon.ico') { response.statusCode=204; response.end(); return; }
      const file = resolve(root, `.${path.endsWith('/') ? `${path}index.html` : path}`), rel = relative(root,file);
      if (rel.startsWith('..') || isAbsolute(rel)) throw new Error('Outside dist');
      const bytes = await readFile(file);
      response.setHeader('Content-Type', ({'.html':'text/html; charset=utf-8','.css':'text/css','.jpg':'image/jpeg'} as Record<string,string>)[extname(file)] ?? 'application/octet-stream');
      response.setHeader('Cache-Control','no-store'); response.end(bytes);
    } catch { response.statusCode = 404; response.end('Not found'); }
  });
  await new Promise<void>(done => server.listen(0,'127.0.0.1',done));
  const address=server.address(); if (!address || typeof address === 'string') throw new Error('Local server unavailable');
  const origin=`http://127.0.0.1:${address.port}`;
  const profile=resolve('.tools',`h4-browser-${process.pid}-${++browserRun}`); await mkdir(profile,{recursive:true});
  const browser=spawn(process.env['H4_BROWSER_PATH'] ?? 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',[
    '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,
    '--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','about:blank',
  ],{windowsHide:true,stdio:['ignore','ignore','pipe']});
  let socket:WebSocket|undefined;
  try {
    const debuggerUrl=await new Promise<string>((done,reject)=>{
      let buffer=''; const timer=setTimeout(()=>reject(new Error('Browser startup timeout')),20000);
      browser.on('error',e=>{clearTimeout(timer);reject(e);});
      browser.stderr.on('data',(data:Buffer)=>{buffer+=data.toString(); const match=buffer.match(/DevTools listening on (ws:\/\/127\.0\.0\.1:\d+\/\S+)/);if(match?.[1]){clearTimeout(timer);done(match[1]);}});
    });
    const debugOrigin=new URL(debuggerUrl).origin.replace('ws:','http:');
    const version=await(await fetch(`${debugOrigin}/json/version`)).json() as {Browser:string};
    const target=await(await fetch(`${debugOrigin}/json/new?about:blank`,{method:'PUT'})).json() as {webSocketDebuggerUrl:string};
    socket=new WebSocket(target.webSocketDebuggerUrl);
    await new Promise<void>((done,reject)=>{socket!.onopen=()=>done();socket!.onerror=()=>reject(new Error('CDP connection failed'));});
    let sequence=0;
    const pending=new Map<number,{done:(v:any)=>void;reject:(e:Error)=>void;timer:ReturnType<typeof setTimeout>}>();
    const events=new Map<string,((params:any)=>void)[]>();
    socket.onmessage=event=>{
      const m=JSON.parse(String(event.data));
      if(m.id){const p=pending.get(m.id);if(!p)return;clearTimeout(p.timer);pending.delete(m.id);if(m.error)p.reject(new Error(JSON.stringify(m.error)));else p.done(m.result);}
      else for(const handler of events.get(m.method)??[])handler(m.params);
    };
    const call=(method:string,params:Record<string,unknown>={}):Promise<any>=>new Promise((done,reject)=>{
      const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error(`CDP timeout:${method}`));},20000);
      pending.set(id,{done,reject,timer});socket!.send(JSON.stringify({id,method,params}));
    });
    const on=(name:string,handler:(p:any)=>void)=>{events.set(name,[...(events.get(name)??[]),handler]);};
    await call('Page.enable');await call('Network.enable');await call('Network.setCacheDisabled',{cacheDisabled:true});
    await call('Network.setBlockedURLs',{urls:['https://*','http://*.usda.gov/*']});
    const evaluate=async(expression:string)=>{const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
    const navigate=async(path:string)=>{
      const loaded=new Promise<void>((done,reject)=>{const timer=setTimeout(()=>reject(new Error('Page load timeout')),20000);events.set('Page.loadEventFired',[()=>{clearTimeout(timer);done();}]);});
      await call('Page.navigate',{url:origin+path});await loaded;
      await evaluate('(async()=>{await Promise.all([...document.images].map(i=>i.decode()));await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));})()');
    };
    return {origin,version:version.Browser,call,on,evaluate,navigate,close:()=>{socket?.close();browser.kill();server.closeAllConnections();server.close();}};
  } catch(e){socket?.close();browser.kill();server.closeAllConnections();server.close();throw e;}
}
