// Project only the model's scoped CSS onto the unchanged real B3 HTML and media.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, dirname, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import postcss from 'postcss'; // Existing Astro dependency, locked by root package-lock.
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const out=resolve(root,'.superdesign/local-review');
const sha=b=>createHash('sha256').update(b).digest('hex');
const original=await readFile(resolve(root,'dist/b3/candidate-01/index.html'),'utf8');
const bindings=JSON.parse(await readFile(resolve(root,'.superdesign/tmp/local-bindings.json'),'utf8'));
if(sha(original)!==bindings.sourceSha256)throw Error('BASELINE_CHANGED');
const variants=[{id:'editorial',label:'Editorial Spread',operator:'pilot-EditorialSpread'}, {id:'chapters',label:'Chapter Rhythm',operator:'pilot-ChapterRhythm'}];
const assets=new Set();
for(const m of bindings.media)for(const key of ['src','srcset','poster','data-src'])for(const item of (m.originalAttributes[key]??'').split(',')){const uri=item.trim().split(/\s+/)[0];if(uri?.startsWith('/'))assets.add(uri);}
const review=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/b3-rich-experience-review.json'),'utf8'));
const media=[];
for(const uri of assets){const path=resolve(root,'dist',uri.slice(1));if(!path.startsWith(resolve(root,'dist')+sep))throw Error('MEDIA_PATH_REJECTED');const bytes=await readFile(path);const expected=review.assets.find(a=>a.uri===uri);if(!expected||sha(bytes)!==expected.file_sha256)throw Error('MEDIA_BYTES_CHANGED');media.push({uri,sha256:sha(bytes),bytes:bytes.length});}
await mkdir(out,{recursive:true});
const manifest={status:'LOCAL_REVIEW_READY_NOT_HUMAN_APPROVED',route:'/b3/candidate-01/',sourceSha256:sha(original),mediaReviewSha256:review.review_sha256,licensedMediaUploaded:false,media,variants:[]};
await writeFile(resolve(out,'baseline.html'),original);
for(const v of variants){
 const providerPath=resolve(root,process.argv.includes('--live')?`.superdesign/tmp/${v.id}.provider.html`:`docs/evidence/design-evaluation/superdesign-20261022/${v.id}.provider.html`);
 const provider=await readFile(providerPath,'utf8');
 const styles=[...provider.matchAll(/<style\b[^>]*\bid=["']pilot-variation-css["'][^>]*>([\s\S]*?)<\/style>/gi)];
 if(styles.length!==1)throw Error(`${v.id}:MISSING_UNIQUE_VARIATION_CSS`);
 const css=styles[0][1];
 if(/url\s*\(|expression\s*\(|javascript:|<\/style/i.test(css))throw Error(`${v.id}:EXTERNAL_OR_EXECUTABLE_CSS`);
 const parsed=postcss.parse(css);
 parsed.walkAtRules(a=>{if(!['media','supports'].includes(a.name.toLowerCase()))throw Error(`${v.id}:UNEXPECTED_AT_RULE:${a.name}`);});
 parsed.walkRules(r=>{
  // Every selector branch must start at the new reusable operator, never a client id.
  let depth=0,start=0;const selectors=[];
  for(let i=0;i<r.selector.length;i++){const c=r.selector[i];if(c==='('||c==='[')depth++;if(c===')'||c===']')depth--;if(c===','&&depth===0){selectors.push(r.selector.slice(start,i));start=i+1;}}
  selectors.push(r.selector.slice(start));
  if(selectors.some(s=>!s.trim().startsWith(`.${v.operator}`)))throw Error(`${v.id}:UNSCOPED_SELECTOR:${r.selector}`);
 });
 parsed.walkDecls(d=>{if(/^(?:filter|backdrop-filter|mix-blend-mode|mask|mask-image)$/.test(d.prop)||/rotate\s*\(/i.test(d.value))throw Error(`${v.id}:UNREVIEWED_MEDIA_TRANSFORM`);if(d.prop==='display'&&d.value==='none'&&!d.parent.selector?.includes('.journal-number'))throw Error(`${v.id}:HIDDEN_CONTENT`);});
 const classPattern=/(<div\b[^>]*\bclass=")([^"]*\bexperience-site\b[^"]*)(")/;
 if(!classPattern.test(original))throw Error('ROOT_CLASS_MISSING');
 let html=original.replace(classPattern,`$1$2 ${v.operator}$3`);
 const injection=`<style id="pilot-variation-css">${css}</style>`;
 html=html.replace('</body>',injection+'</body>');
 // Byte-level round trip proves every original content, link, binding and script survives.
 const restored=html.replace(injection,'').replace(` ${v.operator}"`,'"');
 if(restored!==original)throw Error(`${v.id}:CONTENT_OR_BINDING_CHANGED`);
 await writeFile(resolve(out,`${v.id}.html`),html);
 await writeFile(resolve(out,`${v.id}.css`),css);
 manifest.variants.push({...v,providerSha256:sha(provider),cssSha256:sha(css),htmlSha256:sha(html),cssBytes:Buffer.byteLength(css),originalHtmlRoundTrip:true});
}
await writeFile(resolve(out,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({status:manifest.status,variants:manifest.variants.length,mediaFiles:media.length,mediaBytes:media.reduce((s,a)=>s+a.bytes,0),contentAndBindingsPreserved:true,licensedMediaUploaded:false}));
