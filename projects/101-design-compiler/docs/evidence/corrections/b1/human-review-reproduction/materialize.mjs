// Reproduction recipe: git archive supplies product sources; declared historical
// byte pins supply only frozen evidence and raw package manifests. No live source
// override, install, download, filesystem deletion or repair of root evidence.
import {readFile,writeFile,mkdir,access,copyFile} from 'node:fs/promises';
import {resolve,relative,isAbsolute,dirname} from 'node:path';
import {createHash} from 'node:crypto';
const root=process.cwd(),target=resolve(process.argv[2]??'.tools/corrections/b0/human-review-clean-2/source');
const directory=resolve(process.argv[3]??'docs/evidence/corrections/b1/human-review-reproduction');
const within=(base,path)=>{const p=resolve(base,path),r=relative(base,p);if(r.startsWith('..')||isAbsolute(r))throw Error('OUTSIDE_WORKSPACE');return p;};
within(root,target);within(root,directory);
if(!relative(root,target).replaceAll('\\','/').startsWith('.tools/corrections/b0/')||!target.endsWith('source'))throw Error('NOT_CONTROLLED_SOURCE');
if(!relative(root,directory).replaceAll('\\','/').startsWith('docs/evidence/corrections/b1/'))throw Error('NOT_EVIDENCE_DIRECTORY');
const output=within(directory,'materialization.json');if(await access(output).then(()=>true,()=>false))throw Error('RECEIPT_EXISTS');
const sha=b=>createHash('sha256').update(b).digest('hex'),lf=b=>b.toString('utf8').replaceAll('\r\n','\n');
const manifest=JSON.parse(await readFile(within(root,'docs/evidence/corrections/b1/pre/preservation.json'),'utf8'));
const runtime=JSON.parse(await readFile(within(root,'docs/evidence/corrections/b0/runtime.json'),'utf8'));
const pins=[...manifest.files.filter(f=>f.normalization==='BINARY'),
 {path:'package.json',sha256:runtime.package_sha256},{path:'package-lock.json',sha256:runtime.package_lock_sha256}];
const overlays=[];
for(const pin of pins){
 const source=within(root,pin.path),destination=within(target,pin.path),original=await readFile(source),archived=await readFile(destination);
 if(sha(original)!==pin.sha256)throw Error(`ROOT_PIN_CHANGED:${pin.path}`);
 if(sha(archived)===pin.sha256)continue;
 if(!/\.(html|txt|md|json)$/.test(pin.path)||lf(original)!==lf(archived))throw Error(`NOT_ONLY_LINE_ENDINGS:${pin.path}`);
 await copyFile(source,destination);
 if(sha(await readFile(destination))!==pin.sha256)throw Error('OVERLAY_FAILED');
 overlays.push({path:pin.path,archive_sha256:sha(archived),pinned_sha256:pin.sha256,bytes:original.length,reason:'DECLARED_BYTE_PIN_LINE_ENDINGS_ONLY'});
}
await mkdir(directory,{recursive:true});
const receipt={kind:'B1_REPRODUCTION_BYTE_PIN_OVERLAY',source_tree:'a4d85dcff7257e1761dfcd1aced1c3d98b8df58a',source_archive_sha256:sha(await readFile(resolve(dirname(target),'source.tar'))),
 created_at:new Date().toISOString(),target:relative(root,target).replaceAll('\\','/'),overlays,
 limitations:['Same host/fonts/OS; verified existing dependencies and Node/browser through junctions','Not a fresh installation','Product sources remain from declared Git tree; only verified historical pins/manifests overlay line endings']};
await writeFile(output,JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({status:'PASS',overlays:overlays.length,output:relative(root,output)}));
