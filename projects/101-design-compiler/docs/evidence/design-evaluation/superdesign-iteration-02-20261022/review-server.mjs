// Responsive review harness over unchanged B3 output; no production runtime.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
const root=process.cwd(),dist=resolve(root,'dist'),review=resolve(root,'.superdesign/local-review');
const variants=['baseline','editorial','chapters'],sections={hero:'',journal:'#journal-title',reviews:'#reviews-title',contact:'#contact-title'};
const types={'.html':'text/html; charset=utf-8','.js':'application/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp','.svg':'image/svg+xml','.mp4':'video/mp4'};
createServer(async(req,res)=>{try{
 if(!['GET','HEAD'].includes(req.method)){res.writeHead(405).end();return;}
 const u=new URL(req.url,'http://127.0.0.1:4333');let data,type='text/html; charset=utf-8';
 if(u.pathname==='/'){
  const v=variants.includes(u.searchParams.get('variant'))?u.searchParams.get('variant'):'editorial';
  const mobile=u.searchParams.get('size')==='mobile',section=Object.hasOwn(sections,u.searchParams.get('section'))?u.searchParams.get('section'):'hero';
  const w=mobile?390:1440,h=mobile?844:1000,scale=mobile?.62:.55;
  const names={baseline:'Actual',editorial:'Editorial II · cine y tinta',chapters:'Mesa abierta II · composición por pares'};
  const links=variants.map(x=>`<a href="/?variant=${x}&size=${mobile?'mobile':'desktop'}&section=${section}" ${x===v?'aria-current="page"':''}>${names[x]}</a>`).join('');
  const devices=['desktop','mobile'].map(s=>`<a href="/?variant=${v}&size=${s}&section=${section}">${s==='mobile'?'Móvil':'Escritorio'}</a>`).join('');
  const parts=Object.keys(sections).map(s=>`<a href="/?variant=${v}&size=${mobile?'mobile':'desktop'}&section=${s}">${{hero:'Entrada',journal:'Diario',reviews:'Opiniones',contact:'Contacto'}[s]}</a>`).join('');
  data=Buffer.from(`<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>La mesa abierta · Iteración 02</title><style>body{margin:0;background:#eee;color:#181818;font:14px/1.5 Arial,sans-serif}header{padding:12px 24px;background:white}h1{font:24px Georgia,serif;margin:0 0 8px}nav{display:flex;flex-wrap:wrap;gap:8px 24px;margin-block:6px}a{color:inherit;text-underline-offset:4px}a[aria-current]{font-weight:bold}p{margin:4px 0;font-size:12px}.stage{width:${w*scale}px;height:${h*scale}px;margin:20px auto;max-width:none;background:#fff}iframe{display:block;border:0;width:${w}px;height:${h}px;transform:scale(${scale});transform-origin:top left}</style><header><h1>La mesa abierta · Iteración 02</h1><nav>${links}</nav><nav>${devices}<span>·</span>${parts}<a href="/b3/candidate-01/?pilot=${v}">Abrir página completa ↗</a></nav><p>Mismo contenido y medios. Propuestas pendientes de tu elección. ${mobile?'Frame real de 390 × 844 CSS px; vista al 62%.':'Frame real de 1440 × 1000 CSS px; vista reducida al 55% para compararla.'}</p></header><div class="stage"><iframe title="${names[v]} · ${mobile?'móvil':'escritorio'}" src="/b3/candidate-01/?pilot=${v}${sections[section]}" width="${w}" height="${h}"></iframe></div></html>`);
 }else if(u.pathname==='/b3/candidate-01/'&&u.searchParams.has('pilot')){const id=u.searchParams.get('pilot');if(!variants.includes(id))throw Error();data=await readFile(resolve(review,id+'.html'));}
 else{const p=resolve(dist,'.'+decodeURIComponent(u.pathname));if(!p.startsWith(dist+sep)||decodeURIComponent(u.pathname).split('/').some(x=>x.startsWith('.')))throw Error();const f=extname(p)?p:resolve(p,'index.html');data=await readFile(f);type=types[extname(f)]??'application/octet-stream';}
 res.writeHead(200,{'Content-Type':type,'Content-Length':data.length,'Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; img-src 'self' data:; media-src 'self'; font-src 'self'; frame-src 'self'; connect-src 'none'; base-uri 'none'",'X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?undefined:data);
 }catch{res.writeHead(404).end('No encontrado');}
}).listen(4333,'127.0.0.1',()=>console.log('ITERATION_02 http://127.0.0.1:4333/'));
