import {readFile,writeFile,mkdir,access,copyFile} from 'node:fs/promises';
import {resolve,relative,isAbsolute} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const tree=process.argv[2];if(!/^[a-f0-9]{40}$/.test(tree??''))throw Error('EXPLICIT_STAGED_TREE_REQUIRED');
const root=process.cwd(),base=resolve('.tools/corrections/b0/b2-clean'),target=resolve(base,'source'),directory='docs/evidence/corrections/b2/reproduction';
const rel=relative(root,target);if(isAbsolute(rel)||rel.startsWith('..')||!rel.replaceAll('\\','/').startsWith('.tools/corrections/b0/'))throw Error('OUTSIDE_CONTROLLED_WORKSPACE');
if(await access(base).then(()=>true,()=>false))throw Error('CLEAN_TARGET_ALREADY_EXISTS');
await mkdir(target,{recursive:true});await mkdir(directory,{recursive:true});
const archive=resolve(base,'source.tar');execFileSync('git',['-c',`safe.directory=${root.replaceAll('\\','/')}`,'-c','core.autocrlf=false','archive',tree,'--format=tar',`--output=${archive}`],{windowsHide:true});
execFileSync('tar',['-xf',archive,'-C',target],{windowsHide:true});
const sha=b=>createHash('sha256').update(b).digest('hex'),lf=b=>b.toString().replaceAll('\r\n','\n');
const manifest=JSON.parse(await readFile('docs/evidence/corrections/b2/pre/preservation.json','utf8')),runtime=JSON.parse(await readFile('docs/evidence/corrections/b2/runtime.json','utf8'));
const pins=[...manifest.files.filter(f=>f.normalization==='BINARY'),{path:'package.json',sha256:runtime.package_sha256},{path:'package-lock.json',sha256:runtime.package_lock_sha256}],overlays=[];
for(const pin of pins){
 const original=await readFile(pin.path),archived=await readFile(resolve(target,pin.path));if(sha(original)!==pin.sha256)throw Error(`PIN_CHANGED:${pin.path}`);
 if(sha(archived)===pin.sha256)continue;
 if(!/\.(html|txt|md|json)$/.test(pin.path)||lf(original)!==lf(archived))throw Error(`NOT_LINE_ENDINGS_ONLY:${pin.path}`);
 await copyFile(pin.path,resolve(target,pin.path));overlays.push({path:pin.path,archive_sha256:sha(archived),pinned_sha256:pin.sha256,reason:'DECLARED_HISTORICAL_BYTE_PIN_LINE_ENDINGS_ONLY'});
}
// No installs or browser/font changes; verified existing toolchain is shared.
for(const [path,source] of [['node_modules',resolve('node_modules')],['.tools/node-v24.21.0-win-x64',resolve('.tools/node-v24.21.0-win-x64')],[runtime.browser_root,resolve(runtime.browser_root)]]){
 const dest=resolve(target,path);await mkdir(resolve(dest,'..'),{recursive:true});
 const {symlink}=await import('node:fs/promises');await symlink(source,dest,'junction');
}
await writeFile(`${directory}/materialization.json`,JSON.stringify({kind:'B2_STAGED_TREE_REPRODUCTION',created_at:new Date().toISOString(),source_tree:tree,source_archive_sha256:sha(await readFile(archive)),target:rel.replaceAll('\\','/'),overlays,
 limits:['Same Windows host, current B2 font observation and isolated Edge154','Verified existing Node/dependencies/browser shared through junctions; not a fresh install','No source-code overlay, provider calls, .env copy or creative recorder','Final reports/QA receipts added after this staged engine tree are not input to engine generation']},null,2)+'\n');
console.log(JSON.stringify({status:'MATERIALIZED',source_tree:tree,overlays:overlays.length,target:rel}));
