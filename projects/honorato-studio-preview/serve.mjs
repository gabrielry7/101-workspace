import {createServer} from 'node:http';
import {readFileSync, statSync, realpathSync} from 'node:fs';
import {dirname, resolve, relative, sep, extname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root=dirname(fileURLToPath(import.meta.url)),dist=resolve(root,'dist');
const manifest=JSON.parse(readFileSync(resolve(root,'preview-files.json'),'utf8'));
const sha=b=>createHash('sha256').update(b).digest('hex');
for(const f of manifest.files){
 const p=resolve(dist,f.path);
 if(!p.startsWith(dist+sep)||sha(readFileSync(p))!==f.sha256)throw Error('Preview file changed: '+f.path);
}
if(process.argv.includes('--verify')){
 console.log(`Verified ${manifest.files.length} preview files; ${manifest.snapshot}.`);
}else{
 const port=Number(process.env.PORT||4335);
 if(!Number.isInteger(port)||port<1024||port>65535)throw Error('PORT must be an integer from1024 to65535');
 const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.woff':'font/woff','.woff2':'font/woff2','.txt':'text/plain; charset=utf-8'};
 const server=createServer((req,res)=>{try{
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);return res.end()}
  const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  if(path==='/'){res.writeHead(302,{Location:'/studio/'});return res.end()}
  let file=resolve(dist,'.'+path);
  if(!file.startsWith(dist+sep))throw Error('Rejected path');
  if(statSync(file).isDirectory())file=resolve(file,'index.html');
  const canonical=realpathSync(file);
  if(!canonical.startsWith(realpathSync(dist)+sep))throw Error('Rejected symlink');
  const entry=manifest.files.find(f=>f.path===relative(dist,file).split(sep).join('/'));
  if(!entry)throw Error('Unlisted file');
  const bytes=readFileSync(file);if(sha(bytes)!==entry.sha256)throw Error('Changed file');
  res.writeHead(200,{'Content-Type':mime[extname(file)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Robots-Tag':'noindex, nofollow'});
  res.end(req.method==='HEAD'?undefined:bytes);
 }catch{res.writeHead(404,{'Content-Type':'text/plain'});res.end('Not found in this preview bundle.')}});
 server.on('error',error=>{console.error(error.code==='EADDRINUSE'?`Port ${port} is busy. Set PORT to another number and retry.`:error.message);process.exitCode=1});
 server.listen(port,'127.0.0.1',()=>console.log(`Honorato concepts: http://127.0.0.1:${port}/studio/\nComponent map: http://127.0.0.1:${port}/studio/map/\nCtrl+C stops the preview.`));
}
