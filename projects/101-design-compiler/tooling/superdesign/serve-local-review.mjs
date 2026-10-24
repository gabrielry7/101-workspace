// Read-only localhost preview. This is not a deployment or a commercial backend.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve, dirname, extname, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'), dist=resolve(root,'dist');
const review=resolve(root,'.superdesign/local-review');
const manifest=JSON.parse(await readFile(resolve(review,'manifest.json'),'utf8'));
if(manifest.status!=='LOCAL_REVIEW_READY_NOT_HUMAN_APPROVED')throw Error('REVIEW_NOT_READY');
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8','.webp':'image/webp','.jpg':'image/jpeg','.png':'image/png','.mp4':'video/mp4','.svg':'image/svg+xml'};
const index=`<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>La mesa abierta — revisión Superdesign</title><style>body{font:18px/1.6 system-ui;max-width:52rem;margin:4rem auto;padding:0 1.5rem;color:#181818;background:white}a{display:block;padding:1rem 0;color:inherit}small{display:block;margin-top:2rem}</style><h1>La mesa abierta</h1><p>Piloto de Superdesign sobre la home B3 existente. Mismos textos, enlaces, fotos y vídeo autorizados. Cambia únicamente la composición mediante CSS propuesto por el modelo.</p><a href="/b3/candidate-01/?pilot=baseline">Ver diseño actual →</a><a href="/b3/candidate-01/?pilot=editorial">Explorar Editorial Spread →</a><a href="/b3/candidate-01/?pilot=chapters">Explorar Chapter Rhythm →</a><small>Propuestas pendientes de tu evaluación. Reservas, pedidos, opiniones y redes siguen siendo demostraciones. El motor del proyecto conserva su diseño actual. Los medios se sirven solo en este localhost; no se subieron a Superdesign.</small></html>`;
const server=createServer(async(req,res)=>{
 if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405).end();return;}
 try{
  const url=new URL(req.url,'http://127.0.0.1:4332');
  let data,type='text/html; charset=utf-8';
  if(url.pathname==='/')data=Buffer.from(index);
  else if(url.pathname==='/b3/candidate-01/'&&url.searchParams.has('pilot')){
   const id=url.searchParams.get('pilot');if(!['baseline','editorial','chapters'].includes(id))throw Error('NOT_FOUND');data=await readFile(resolve(review,`${id}.html`));
  }else{
   const path=resolve(dist,'.'+decodeURIComponent(url.pathname));
   if(!path.startsWith(dist+sep)||decodeURIComponent(url.pathname).split('/').some(p=>p.startsWith('.')))throw Error('NOT_FOUND');
   const file=extname(path)?path:resolve(path,'index.html');
   data=await readFile(file);type=types[extname(file)]??'application/octet-stream';
  }
  res.writeHead(200,{'Content-Type':type,'Content-Length':data.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; img-src 'self' data:; media-src 'self'; font-src 'self'; connect-src 'none'; frame-src 'none'; base-uri 'none'"});
  res.end(req.method==='HEAD'?undefined:data);
 }catch{res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'}).end('No encontrado');}
});
server.listen(4332,'127.0.0.1',()=>console.log('LOCAL_REVIEW http://127.0.0.1:4332/'));
