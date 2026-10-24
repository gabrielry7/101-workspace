import {readFile,writeFile,mkdir,access,copyFile,symlink} from 'node:fs/promises';
import {resolve,relative,isAbsolute} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const tree=process.argv[2];if(!/^[a-f0-9]{40}$/.test(tree??''))throw Error('EXPLICIT_STAGED_TREE_REQUIRED');
const root=process.cwd(),base=resolve('.tools/corrections/b0/b2-demo-clean'),target=resolve(base,'source'),directory='docs/evidence/corrections/b2-demo/reproduction';
if(await access(base).then(()=>true,()=>false))throw Error('CONTROLLED_TARGET_EXISTS');
const within=(base,path)=>{const p=resolve(base,path),r=relative(base,p);if(r.startsWith('..')||isAbsolute(r))throw Error('OUTSIDE_WORKSPACE');return p;};within(root,target);
await mkdir(target,{recursive:true});await mkdir(directory,{recursive:true});const archive=resolve(base,'source.tar');
execFileSync('git',['-c',`safe.directory=${root.replaceAll('\\','/')}`,'-c','core.autocrlf=false','archive',tree,'--format=tar',`--output=${archive}`],{windowsHide:true});execFileSync('tar',['-xf',archive,'-C',target],{windowsHide:true});
const sha=b=>createHash('sha256').update(b).digest('hex');const runtime=JSON.parse(await readFile('docs/evidence/corrections/b2/runtime.json','utf8'));
const pack=JSON.parse(await readFile('data/media/demo-v1/pixabay-fictional.json','utf8')),private_files=[];
for(const f of pack.files){
 if(!f.path.startsWith('.tools/b2-demo/originals/')&&!f.path.startsWith('public/media/b2-fictional/'))throw Error('NON_PACKAGE_ASSET_PATH');
 const from=within(root,f.path),to=within(target,f.path),b=await readFile(from);if(sha(b)!==f.sha256||b.length!==f.bytes)throw Error('PRIVATE_PACKAGE_BYTES_CHANGED');await mkdir(resolve(to,'..'),{recursive:true});await copyFile(from,to);
 private_files.push({path:f.path,bytes:b.length,sha256:sha(b),method:'EXPLICIT_PRIVATE_AUTHORIZED_PACKAGE_COPY_NOT_GIT_OR_DOWNLOAD'});
}
for(const [path,source] of [['node_modules',resolve('node_modules')],['.tools/node-v24.21.0-win-x64',resolve('.tools/node-v24.21.0-win-x64')],[runtime.browser_root,resolve(runtime.browser_root)]]){const p=within(target,path);await mkdir(resolve(p,'..'),{recursive:true});await symlink(source,p,'junction');}
await writeFile(`${directory}/materialization.json`,JSON.stringify({kind:'B2_FICTIONAL_DEMO_PRIVATE_PACKAGE_REPRODUCTION',created_at:new Date().toISOString(),source_tree:tree,source_archive_sha256:sha(await readFile(archive)),target:relative(root,target).replaceAll('\\','/'),private_files,
 no_env:!await access(resolve(target,'.env')).then(()=>true,()=>false),provider_requests:0,
 limits:['Git sources plus 14 specifically authorized private media files; not a self-contained public clone','Same host/current B2 fonts, existing verified Node/dependencies/browser junctions','No raw API caches, signed source URLs, secrets, rejected candidates, new installs or provider calls copied']},null,2)+'\n');console.log(JSON.stringify({status:'PASS_MATERIALIZED',private_files:private_files.length,tree}));
