import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const before=resolve('dist'),after=resolve('.tools/claude-worktrees/restaurant-journal-pilot-01/dist');
async function tree(dir,prefix=''){const files=[];for(const e of await readdir(resolve(dir,prefix),{withFileTypes:true})){const path=prefix+e.name;if(e.isDirectory())files.push(...await tree(dir,path+'/'));else files.push(path);}return files.sort();}
const a=await tree(before),b=await tree(after),html=a.filter(p=>p.endsWith('.html'));
const normalize=s=>s.replace(/<style\b[^>]*>[\s\S]*?<\/style>/g,'<style>ALLOWED_STYLESHEET_CHANGE</style>').replace(/href="\/_astro\/[^"<>]+\.css"/g,'href="/_astro/STYLESHEET.css"');
const changedMarkup=[];
for(const path of html){if(normalize(await readFile(resolve(before,path),'utf8'))!==normalize(await readFile(resolve(after,path),'utf8')))changedMarkup.push(path);}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const scripts=a.filter(p=>p.endsWith('.js')),media=a.filter(p=>p.startsWith('media/')&&/\.(jpe?g|png|webp|svg|mp4|webm)$/i.test(p));
const changedAssets=[];
for(const path of [...scripts,...media]){if(sha(await readFile(resolve(before,path)))!==sha(await readFile(resolve(after,path))))changedAssets.push(path);}
const cssBytes=async(root,paths)=>(await Promise.all(paths.filter(p=>p.endsWith('.css')).map(p=>readFile(resolve(root,p))))).reduce((n,v)=>n+v.length,0);
const homeBefore=await readFile(resolve(before,'b3/candidate-01/index.html'),'utf8'),homeAfter=await readFile(resolve(after,'b3/candidate-01/index.html'),'utf8');
const inlineBytes=s=>[...s.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)].reduce((n,m)=>n+Buffer.byteLength(m[1]),0);
const result={htmlPages:html.length,afterHtmlPages:b.filter(p=>p.endsWith('.html')).length,markupIdenticalExcludingCss:changedMarkup.length===0,changedMarkup,scriptFiles:scripts.length,mediaFiles:media.length,jsAndMediaPayloadByteIdentical:changedAssets.length===0,changedAssets,beforeExternalCssBytes:await cssBytes(before,a),afterExternalCssBytes:await cssBytes(after,b),targetHtmlBytesBefore:Buffer.byteLength(homeBefore),targetHtmlBytesAfter:Buffer.byteLength(homeAfter),targetInlineCssBytesBefore:inlineBytes(homeBefore),targetInlineCssBytesAfter:inlineBytes(homeAfter),limits:['HTML normalization removes inline CSS and normalizes stylesheet hashed URLs only; all other markup, copy, bindings and scripts remain compared','Media comparison covers payload formats, not copied Git metadata line endings','Build totals, not network transfer or Core Web Vitals']};
await writeFile('.tools/claude-code/restaurant-journal-pilot-01/preservation.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));if(changedMarkup.length||changedAssets.length)process.exitCode=1;
